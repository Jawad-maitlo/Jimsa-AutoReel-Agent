import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from . import __version__
from .config import get_settings
from .database import SessionLocal, init_db
from .models import AppSetting
from .routers import projects, reels, social, system, videos
from .security import RedactingFilter
from .services.publishing import dispatch_due_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
for handler in logging.getLogger().handlers:
    handler.addFilter(RedactingFilter())
logger = logging.getLogger(__name__)


async def publishing_scheduler():
    while True:
        try:
            await asyncio.to_thread(dispatch_due_jobs)
        except Exception as exc:
            logger.error("Publishing scheduler error: %s", exc)
        await asyncio.sleep(20)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with SessionLocal() as db:
        for item in db.query(AppSetting).all():
            if hasattr(settings, item.key):
                setattr(settings, item.key, item.value)
    task = asyncio.create_task(publishing_scheduler())
    logger.info("Jimsa Autoreel Agent %s ready", __version__)
    yield
    task.cancel()


settings = get_settings()
app = FastAPI(title=settings.app_name, version=__version__, description="Local-first AI reel editing and publishing API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_credentials=False, allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.error("Unhandled API error on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "An unexpected local server error occurred. Check backend logs."})


app.include_router(system.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(reels.router, prefix="/api")
app.include_router(social.router, prefix="/api")


DIST_DIR = Path(__file__).resolve().parents[2] / "dist"
if (DIST_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")


@app.get("/", include_in_schema=False)
def root():
    if (DIST_DIR / "index.html").is_file():
        return FileResponse(DIST_DIR / "index.html")
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if full_path.startswith(("api/", "docs", "openapi.json")):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if (DIST_DIR / "index.html").is_file():
        return FileResponse(DIST_DIR / "index.html")
    return JSONResponse(status_code=404, content={"detail": "Not found"})
