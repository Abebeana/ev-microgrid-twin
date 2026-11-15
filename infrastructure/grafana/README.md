# Grafana reporting

`provisioning/` configures the local Prometheus datasource. `dashboards/` contains
the existing PostgreSQL reporting dashboards. `tools/` builds, exports, validates,
publishes, and verifies them. The PostgreSQL dashboards need the separate reporting
database and Business Charts plugin described by the deployment tools; the local
Compose monitoring profile does not provision that reporting database.

```bash
python infrastructure/grafana/tools/build_dashboards.py
python infrastructure/grafana/tools/export_replay_tables.py /tmp/microgrid-grafana-export
```

For a reporting deployment, prepare its PostgreSQL database using
`tools/prepare_reporting_database.sh` on that host. Set `GRAFANA_URL` and
`GRAFANA_TOKEN` (or `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`). For first
publication, `GRAFANA_DATABASE_PASSWORD_FILE` identifies the database password
file. Then run `publish_dashboards.py`, or `update_dashboards.py` for existing
resources. Validate with `validate_dashboard_queries.py` and
`verify_deployed_dashboards.py`. Nothing is published during normal app startup.

Deployed `sofie-*` UIDs and database identifiers are preserved to avoid changing
existing resources. Local filenames describe each dashboard's purpose.

The exporter now reads `TWIN_REPLAY_DIR` (default `data/processed/replay`) and
validates the JSON manifest and CSV checksums. It writes CSV gzip exports for the
optional PostgreSQL reporting adapter; no SQLite measurement store is used.
