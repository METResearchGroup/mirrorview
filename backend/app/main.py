import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import feedback_router, generate_router
from app.db.session import dispose_engine, init_engine, is_persistence_enabled
from lib.load_env_vars import EnvVarsContainer

logger = logging.getLogger(__name__)

def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    # Always allow local Next.js dev.
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    return origins


@asynccontextmanager
async def lifespan(_: FastAPI):
    if is_persistence_enabled():
        database_url = EnvVarsContainer.get_env_var("DATABASE_URL", required=True)
        init_engine(database_url)
    try:
        yield
    finally:
        await dispose_engine()


app = FastAPI(title="MirrorView Backend", version="0.2.0", lifespan=lifespan)

allow_origins = _parse_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

app.include_router(generate_router)
app.include_router(feedback_router)
