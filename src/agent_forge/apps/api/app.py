"""API app placeholder."""

from fastapi import FastAPI

app = FastAPI(title="agent-forge")


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

