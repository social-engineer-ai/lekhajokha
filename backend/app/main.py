import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, clients, bank_accounts, bank_statements, transactions, jobs, invoices
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure MinIO bucket exists
    try:
        from app.services.storage_service import ensure_bucket
        ensure_bucket()
        logger.info("MinIO bucket ready")
    except Exception as e:
        logger.warning(f"MinIO not available (will retry on first upload): {e}")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.BACKEND_CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(bank_accounts.router, prefix="/api/v1")
app.include_router(bank_statements.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
