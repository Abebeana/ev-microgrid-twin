# Backend

Run from the repository root with `make api` or
`.venv/bin/python -m uvicorn backend.main:app`.

`main.py` composes lifecycle, middleware, and routers. `api/routes/` handles HTTP
requests. Configuration, ingestion, historical telemetry, charging, alarms,
forecasting, electrical power flow, battery physics, optimization, operations,
streaming, topology, and reinforcement learning have separate modules. Imports use
`backend.<responsibility>.<module>`.

Dependencies and the Python environment are defined at the repository root.
See `../docs/architecture.md` for boundaries and `../docs/data-pipeline.md` for provenance.
