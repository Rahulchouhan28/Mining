from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import projects

app = FastAPI(
    title="Mining Plan Generator API",
    version="0.1.0",
    description="Backend for the year-wise mining plan generator (MCDR / DGM Rajasthan style).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mining-plan-generator-api"}
