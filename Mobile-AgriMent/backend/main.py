import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from database.connection import engine, Base
from routes.auth import router as auth_router
from routes.detect import router as detect_router
from routes.notifications import router as notifications_router

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def _ensure_notification_detection_id_column() -> None:
    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA table_info(notifications)"))
        columns = {row[1] for row in result.fetchall()}
        if "detection_id" not in columns:
            await conn.execute(text("ALTER TABLE notifications ADD COLUMN detection_id VARCHAR(36)"))

        result = await conn.execute(text("PRAGMA table_info(detections)"))
        det_columns = {row[1] for row in result.fetchall()}
        if "latitude" not in det_columns:
            await conn.execute(text("ALTER TABLE detections ADD COLUMN latitude FLOAT"))
        if "longitude" not in det_columns:
            await conn.execute(text("ALTER TABLE detections ADD COLUMN longitude FLOAT"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Demarrage de l'API AgriMent...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_notification_detection_id_column()
    logger.info("Database tables created")
    yield
    logger.info("Arret de l'API AgriMent...")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Systeme de detection de ravageurs par IA et alertes regionales pour les agriculteurs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path

upload_dir = Path(settings.UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

app.include_router(auth_router, prefix="/api")
app.include_router(detect_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


@app.get("/health")
async def health_check():
    return {"status": "sain", "service": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/web", response_class=HTMLResponse)
async def serve_web_dashboard():
    dashboard_path = Path(__file__).parent / "web_dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Web Dashboard Not Found</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=settings.DEBUG)
