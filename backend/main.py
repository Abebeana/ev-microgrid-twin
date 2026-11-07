"""Small API entry point for the EV microgrid twin."""

from fastapi import FastAPI

app = FastAPI(title="EV Microgrid Twin API")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
