"""Reconstruct charger observations and sessions with explicit source validation."""

from dataclasses import dataclass, field

from backend.ingestion.microgrid import Mean, source_timestamp
from backend.ingestion.value_conversion import _nullable, _number


def inventory(source):
    columns = source.indices(
        "charge_box", ("charge_box_id", "charge_point_vendor", "charge_point_model", "fw_version")
    )
    boxes = [
        tuple(_nullable(row[index]) for index in columns.values())
        for row in source.rows("charge_box")
    ]
    box_ids = {row[0] for row in boxes}
    columns = source.indices("connector", ("connector_pk", "charge_box_id", "connector_id"))
    connectors = {}
    for row in source.rows("connector"):
        if row[columns["connector_id"]] != 1:
            continue
        key, box = int(row[columns["connector_pk"]]), row[columns["charge_box_id"]]
        if key in connectors or box not in box_ids:
            raise ValueError("Duplicate connector or unknown wallbox in source inventory")
        connectors[key] = box
    if not connectors or len(set(connectors.values())) != len(connectors):
        raise ValueError("Expected one primary charging connector per wallbox")
    return boxes, connectors


@dataclass
class PowerReading:
    watts: Mean = field(default_factory=Mean)
    last: str = ""


def power_readings(source, connectors, config):
    columns = source.indices(
        "connector_meter_value", ("connector_pk", "value_timestamp", "value", "measurand", "unit")
    )
    readings = {}
    invalid = 0
    for row in source.rows("connector_meter_value"):
        box = connectors.get(row[columns["connector_pk"]])
        if (
            box is None
            or row[columns["measurand"]] != "Power.Active.Import"
            or row[columns["unit"]] != "W"
        ):
            continue
        watts = _number(row[columns["value"]])
        if watts is None or not 0 <= watts <= config.charger_validation_max_kw * 1000:
            invalid += 1
            continue
        stamp = source_timestamp(row[columns["value_timestamp"]])
        reading = readings.setdefault((stamp[:16], box), PowerReading())
        reading.watts.add(watts)
        reading.last = max(reading.last, stamp)
    return [
        (minute, box, reading.watts.scaled(0.001), reading.watts.count, reading.last)
        for (minute, box), reading in readings.items()
    ], invalid


def status_events(source, connectors):
    columns = source.indices(
        "connector_status", ("connector_pk", "status_timestamp", "status", "error_code")
    )
    events = {}
    conflicts = set()
    for row in source.rows("connector_status"):
        connector = row[columns["connector_pk"]]
        if connector not in connectors:
            continue
        stamp = source_timestamp(row[columns["status_timestamp"]])
        status = row[columns["status"]]
        record = (
            connector,
            connectors[connector],
            stamp,
            status,
            _nullable(row[columns["error_code"]]),
        )
        key = (connector, stamp, status)
        if key in events and events[key] != record:
            conflicts.add(key)
            codes = set((events[key][4] or "").split(" | ")) | {record[4] or ""}
            record = (*record[:4], " | ".join(sorted(codes - {""})) or None)
        events[key] = record
    return events.values(), len(conflicts)


def charging_sessions(source, connectors):
    columns = source.indices(
        "transaction_stop", ("transaction_pk", "stop_timestamp", "stop_value", "stop_reason")
    )
    stops = {}
    stop_count = 0
    for row in source.rows("transaction_stop"):
        stop_count += 1
        transaction = int(row[columns["transaction_pk"]])
        stamp = source_timestamp(row[columns["stop_timestamp"]])
        if transaction not in stops or stamp >= stops[transaction][0]:
            stops[transaction] = (
                stamp,
                _number(row[columns["stop_value"]]),
                _nullable(row[columns["stop_reason"]]),
            )
    columns = source.indices(
        "transaction_start", ("transaction_pk", "connector_pk", "start_timestamp", "start_value")
    )
    sessions = {}
    for row in source.rows("transaction_start"):
        connector = row[columns["connector_pk"]]
        if connector not in connectors:
            continue
        transaction = int(row[columns["transaction_pk"]])
        stamp = source_timestamp(row[columns["start_timestamp"]])
        ending = stops.get(transaction, (None, None, None))
        if ending[0] is not None and ending[0] < stamp:
            raise ValueError(f"Session {transaction} stops before it starts")
        record = (
            transaction,
            connectors[connector],
            stamp,
            ending[0],
            _number(row[columns["start_value"]]),
            ending[1],
            ending[2],
        )
        if transaction in sessions and sessions[transaction] != record:
            raise ValueError(f"Conflicting session starts: {transaction}")
        sessions[transaction] = record
    return list(sessions.values()), {
        "duplicate_stops": stop_count - len(stops),
        "unmatched_stops": len(stops.keys() - sessions.keys()),
    }
