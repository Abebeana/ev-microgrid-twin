# EV Microgrid Twin

Minimal starting point for the EV microgrid twin. The API and frontend are intentionally small; data ingestion, site configuration, and infrastructure can be added as the project develops. The dataset link is in [dataset.md](dataset.md).

## Structure

- `backend/main.py` — FastAPI entry point, directly inside `backend`.
- `frontend/` — React and Vite starter page.
- `config/`, `data/`, `docs/`, `EDA/`, `infra/` — existing placeholders for future project work.

## Run locally

Start the API:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The API health endpoint is http://localhost:8000/api/health, and API docs are at http://localhost:8000/docs.
