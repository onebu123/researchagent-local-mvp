from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import export, literature, logs, manuscript, outputs, projects, review, trust, uploads, workflow
from app.database import initialize_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="ResearchAgent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "research-agent-api", "version": "0.1.0"}


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
