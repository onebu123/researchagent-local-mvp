from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    export,
    intelligence,
    literature,
    logs,
    manuscript,
    outputs,
    projects,
    review,
    system,
    trust,
    uploads,
    workflow,
)
from app.config import settings
from app.database import initialize_database

APP_VERSION = "v2.0.1-dev"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="ResearchAgent API", version=APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "research-agent-api", "version": APP_VERSION}


app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(uploads.router, prefix="/api", tags=["uploads"])
app.include_router(workflow.router, prefix="/api", tags=["workflow"])
app.include_router(outputs.router, prefix="/api", tags=["outputs"])
app.include_router(literature.router, prefix="/api", tags=["literature"])
app.include_router(review.router, prefix="/api", tags=["review"])
app.include_router(manuscript.router, prefix="/api", tags=["manuscript"])
app.include_router(logs.router, prefix="/api", tags=["logs"])
app.include_router(trust.router, prefix="/api", tags=["trust"])
app.include_router(export.router, prefix="/api", tags=["export"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(intelligence.router, prefix="/api", tags=["literature-intelligence"])
