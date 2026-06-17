from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agent,
    auto_scientist,
    export,
    human_review,
    intelligence,
    jobs,
    literature,
    logs,
    manuscript,
    outputs,
    paper_writer,
    projects,
    review,
    system,
    trust,
    uploads,
    workflow,
)
from app.config import settings
from app.database import initialize_database

APP_VERSION = "v3.0.0-rc1"


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
app.include_router(human_review.router, prefix="/api", tags=["human-review"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(intelligence.router, prefix="/api", tags=["literature-intelligence"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])
app.include_router(agent.router, prefix="/api", tags=["agent"])
app.include_router(auto_scientist.router, prefix="/api", tags=["auto-scientist"])
app.include_router(paper_writer.router, prefix="/api", tags=["paper-writer"])
