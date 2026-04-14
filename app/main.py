from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.core.database import init_db
import app.models  # noqa: F401 — register all models before init_db
from app.api import customers, documents, events, search, chat, audit, incident
from app.api import auth, hybrid_search, email, documents_v2

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MSP Archive Platform...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down MSP Archive Platform...")


app = FastAPI(
    title="MSP Archive Platform",
    description="MSP 운영 기록 중심 플랫폼 - 문서 저장, 검색, 채팅, 이벤트 관리를 통합 제공",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url)}
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(documents_v2.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(hybrid_search.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(incident.router, prefix="/api/v1")
app.include_router(email.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "msp-archive"}


@app.get("/")
async def root():
    return {
        "service": "MSP Archive Platform",
        "version": "0.1.0",
        "docs": "/docs"
    }
