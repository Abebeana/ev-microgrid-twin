"""Build one recorded minute as a Neo4j property graph."""

from __future__ import annotations

from backend.configuration.site import load_site_config
from backend.telemetry import history
from backend.topology.projection import project_snapshot


def build_site_graph(at: str | None = None):
    current = history.snapshot(at)
    return project_snapshot(
        load_site_config(),
        recorded_at=current["raw_time"],
        solar_kw=current["solar_kw"],
        battery_soc_pct=current["battery_soc_pct"],
        battery_temp_c=current["battery_temp_c"],
        wallboxes=current["wallboxes"],
    )
