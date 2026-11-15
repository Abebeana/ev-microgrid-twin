"""Project one recorded minute into the Neo4j property-graph contract."""

from __future__ import annotations

from backend.configuration.site import SiteConfig

CATALOG_KINDS = {"site", "solar", "battery", "bus", "charger", "other"}


def project_snapshot(
    config: SiteConfig,
    *,
    recorded_at: str,
    solar_kw: float | None,
    battery_soc_pct: float | None,
    battery_temp_c: float | None,
    wallboxes: list[dict],
    received_at: str | None = None,
) -> dict:
    """Build nodes and typed edges for one minute. Nothing is written here."""
    counts = {kind: sum(asset.kind == kind for asset in config.assets) for kind in ("solar", "battery")}
    bus = next(asset for asset in config.assets if asset.kind == "bus")
    site_id = f"site:{config.site_id}"
    sample_id = "sample:latest"
    nodes: list[dict] = [
        {
            "id": site_id,
            "kind": "site",
            "name": config.site_name,
            "islanded": True,
            "wallbox_id": None,
        }
    ]
    edges: list[dict] = []
    for asset in config.assets:
        node_id = f"asset:{asset.id}"
        value, unit, attribution = _asset_measurement(
            asset.kind, counts, solar_kw, battery_soc_pct
        )
        node = {
            "id": node_id,
            "kind": asset.kind,
            "name": asset.name,
            "value": value,
            "wallbox_id": None,
        }
        if unit is not None:
            node["unit"] = unit
        if attribution is not None:
            node["attribution"] = attribution
        nodes.append(node)
        edges.append({"source": site_id, "target": node_id, "relation": "HAS_ASSET"})
        if asset.kind in {"solar", "battery"}:
            edges.append(
                {
                    "source": node_id,
                    "target": sample_id,
                    "relation": "OBSERVED_IN",
                    "value": value,
                    "unit": unit,
                    "quality": _quality(attribution),
                }
            )
        if asset.connected_to:
            edges.append(
                {
                    "source": node_id,
                    "target": f"asset:{asset.connected_to}",
                    "relation": "CONNECTED_TO",
                    "medium": "islanded_ac_bus",
                }
            )
    for box in wallboxes:
        node_id = f"wallbox:{box['id']}"
        node = {
            "id": node_id,
            "kind": "charger",
            "name": box["id"],
            "value": box.get("power_kw"),
            "unit": "kW",
            "status": box.get("status") or "Unknown",
            "wallbox_id": box["id"],
        }
        if box.get("vendor"):
            node["vendor"] = box["vendor"]
        if box.get("model"):
            node["model"] = box["model"]
        nodes.append(node)
        edges.append({"source": site_id, "target": node_id, "relation": "HAS_ASSET"})
        edges.append(
            {
                "source": f"asset:{bus.id}",
                "target": node_id,
                "relation": "CONNECTED_TO",
                "medium": "islanded_ac_bus",
            }
        )
        edges.append(
            {
                "source": node_id,
                "target": sample_id,
                "relation": "OBSERVED_IN",
                "value": box.get("power_kw"),
                "unit": "kW",
                "status": node["status"],
                "quality": "observed" if box.get("power_kw") is not None else "missing",
            }
        )
    sample = {
        "id": sample_id,
        "kind": "telemetry_sample",
        "name": recorded_at,
        "recorded_at": recorded_at,
        "wallbox_id": None,
    }
    if received_at is not None:
        sample["received_at"] = received_at
    nodes.append(sample)
    edges.append({"source": site_id, "target": sample_id, "relation": "HAS_SAMPLE"})
    alerts = _alerts(
        config,
        battery_soc_pct=battery_soc_pct,
        battery_temp_c=battery_temp_c,
        wallboxes=wallboxes,
    )
    for alert in alerts:
        nodes.append(
            {
                "id": alert["id"],
                "kind": "alert",
                "name": alert["name"],
                "rule": alert["rule"],
                "severity": alert["severity"],
                "about": alert["about"],
                "wallbox_id": None,
            }
        )
        edges.append(
            {
                "source": sample_id,
                "target": alert["id"],
                "relation": "RAISED",
                "rule": alert["rule"],
            }
        )
        for subject in alert["about"]:
            edges.append({"source": alert["id"], "target": subject, "relation": "ABOUT"})
    note = "Configured islanded topology in Neo4j; no utility grid connection"
    if counts["solar"] > 1 or counts["battery"] > 1:
        note += ". Site-level PV and battery measurements cannot be attributed to individual units"
    return {"nodes": nodes, "edges": edges, "note": note, "alerts": alerts}


def _asset_measurement(kind: str, counts: dict[str, int], solar_kw, battery_soc_pct):
    if kind == "solar":
        if counts["solar"] != 1:
            return None, None, "withheld_multiple"
        if solar_kw is None:
            return None, None, "measurement_missing"
        return solar_kw, "kW", "single_asset"
    if kind == "battery":
        if counts["battery"] != 1:
            return None, None, "withheld_multiple"
        if battery_soc_pct is None:
            return None, None, "measurement_missing"
        return battery_soc_pct, "percent", "single_asset"
    return None, None, None


def _quality(attribution: str | None) -> str:
    if attribution == "single_asset":
        return "observed"
    if attribution == "withheld_multiple":
        return "withheld"
    return "missing"


def _alerts(config: SiteConfig, *, battery_soc_pct, battery_temp_c, wallboxes: list[dict]) -> list[dict]:
    batteries = [f"asset:{asset.id}" for asset in config.assets if asset.kind == "battery"]
    site_id = f"site:{config.site_id}"
    alerts = []
    if battery_soc_pct is not None and battery_soc_pct < config.battery_low_soc_alarm_pct:
        alerts.append(
            {
                "id": "alert:low_soc",
                "rule": "low_soc",
                "name": "Battery below configured SoC threshold",
                "severity": "warning",
                "about": batteries or [site_id],
            }
        )
    if battery_temp_c is not None and battery_temp_c > config.battery_high_temp_alarm_c:
        alerts.append(
            {
                "id": "alert:high_temp",
                "rule": "high_temp",
                "name": "Battery above configured temperature threshold",
                "severity": "warning",
                "about": batteries or [site_id],
            }
        )
    for box in wallboxes:
        if box.get("status") == "Faulted" and not box.get("status_stale"):
            alerts.append(
                {
                    "id": f"alert:fault:{box['id']}",
                    "rule": "charger_fault",
                    "name": f"{box['id']} reported a fault",
                    "severity": "warning",
                    "about": [f"wallbox:{box['id']}"],
                }
            )
    observed = [box for box in wallboxes if box.get("power_kw") is not None]
    if len(observed) < len(wallboxes):
        missing = [f"wallbox:{box['id']}" for box in wallboxes if box.get("power_kw") is None]
        alerts.append(
            {
                "id": "alert:coverage",
                "rule": "coverage",
                "name": f"Only {len(observed)}/{len(wallboxes)} wallboxes reported power",
                "severity": "warning",
                "about": missing or [site_id],
            }
        )
    return alerts
