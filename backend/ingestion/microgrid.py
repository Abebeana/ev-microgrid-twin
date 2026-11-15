"""Aggregate ordered source samples without substituting missing measurements."""

from dataclasses import dataclass, field
from datetime import datetime

from backend.configuration.site import SiteConfig
from backend.ingestion.value_conversion import _missing, _number


def source_timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid source timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"Invalid source timestamp: {value}") from error
    if parsed.tzinfo is not None or len(value) < 19 or value[10] != " ":
        raise ValueError("Expected an unzoned source timestamp with seconds")
    return value


@dataclass
class Mean:
    total: float = 0.0
    count: int = 0

    def add(self, value: float) -> None:
        self.total += value
        self.count += 1

    def scaled(self, scale: float = 1) -> float | None:
        return self.total / self.count * scale if self.count else None


@dataclass
class Minute:
    time: str
    samples: int = 0
    solar: Mean = field(default_factory=Mean)
    soc: Mean = field(default_factory=Mean)
    temperature: Mean = field(default_factory=Mean)
    power: Mean = field(default_factory=Mean)
    bad_soc: int = 0
    bad_solar: int = 0

    def record(self) -> tuple:
        return (
            self.time,
            self.samples,
            self.solar.scaled(0.001),
            self.solar.count,
            self.soc.scaled(),
            self.temperature.scaled(0.1),
            self.power.scaled(0.01),
            self.bad_soc,
            self.bad_solar,
        )


def aggregate_microgrid(source, config: SiteConfig) -> tuple[list[tuple], dict]:
    columns = source.indices("logging", ("timestamp", "p_actual", "bat_soc", "bat_temp", "P_sum"))
    records = []
    minute = None
    first = last = None
    missing_solar = 0
    for row in source.rows("logging"):
        stamp = source_timestamp(row[columns["timestamp"]])
        if minute is not None and stamp[:16] < minute.time:
            raise ValueError("SOFIE logging rows must be ordered by minute")
        first = stamp if first is None else min(first, stamp)
        last = stamp if last is None else max(last, stamp)
        if minute is None or minute.time != stamp[:16]:
            if minute is not None:
                records.append(minute.record())
            minute = Minute(stamp[:16])
        minute.samples += 1
        solar_raw = row[columns["p_actual"]]
        solar = _number(solar_raw)
        if _missing(solar_raw):
            missing_solar += 1
        elif solar is None or not 0 <= solar <= config.solar_validation_max_kw * 1000:
            minute.bad_solar += 1
        else:
            minute.solar.add(solar)
        soc_raw = row[columns["bat_soc"]]
        soc = _number(soc_raw)
        if not _missing(soc_raw) and (soc is None or not 0 <= soc <= 100):
            minute.bad_soc += 1
        elif soc is not None:
            minute.soc.add(soc)
        temperature = _number(row[columns["bat_temp"]])
        if (
            temperature is not None
            and config.battery_temperature_min_c * 10
            <= temperature
            <= config.battery_temperature_max_c * 10
        ):
            minute.temperature.add(temperature)
        power = _number(row[columns["P_sum"]])
        if power is not None:
            minute.power.add(power)
    if minute is None:
        raise ValueError("SOFIE logging table is empty")
    records.append(minute.record())
    return records, {
        "first_raw": first,
        "last_raw": last,
        "missing_solar": missing_solar,
        "bad_soc": sum(row[7] for row in records),
        "bad_solar": sum(row[8] for row in records),
    }
