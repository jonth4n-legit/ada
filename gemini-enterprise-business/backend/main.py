"""
Gemini Ultra Gateway - Main Application
A comprehensive Gemini Business API gateway with advanced media generation features

Features:
- OpenAI-compatible chat completions API
- Advanced Image Studio (like Google Whisk/ImageFX)
- Advanced Video Studio (like Google Flow/VideoFX)
- Multi-account load balancing
- Session management and caching
"""

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse

from core.config import Config
from core.account_pool import get_account_pool, close_http_client
from core.session_manager import get_session_manager
from api.openai_compat import router as openai_router
from api.media_studio import router as media_router
from api.admin import router as admin_router
from database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("gemini.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("=" * 60)
    logger.info("  GEMINI ULTRA GATEWAY")
    logger.info("  Advanced API Gateway for Gemini Business")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Initialize account pool
    pool = get_account_pool()
    stats = pool.get_stats()
    logger.info(f"Loaded {stats['total_accounts']} accounts")
    
    # Initialize session manager
    session_mgr = get_session_manager()
    
    # Log proxy status
    if Config.PROXY:
        logger.info(f"Proxy configured: {Config.PROXY}")
    else:
        logger.info("Direct connection (no proxy)")
    
    logger.info(f"Server starting on {Config.HOST}:{Config.PORT}")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await close_http_client()
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Gemini Ultra Gateway",
    description=(
        "A comprehensive API gateway for Gemini Business with advanced features:\n\n"
        "- **OpenAI-compatible API**: Drop-in replacement for OpenAI's chat completions\n"
        "- **Image Studio**: Advanced image generation with Whisk-like ingredients mixing\n"
        "- **Video Studio**: Video generation with Flow-like extension and interpolation\n"
        "- **Multi-account Support**: Load balancing across multiple Gemini accounts\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(openai_router)
app.include_router(media_router)
app.include_router(admin_router)

# Mount static files (admin UI)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception:
    logger.warning("Static files directory not found, admin UI will not be available")


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Gemini Ultra Gateway",
        "version": "1.0.0",
        "description": "Advanced Gemini Business API Gateway",
        "features": [
            "OpenAI-compatible chat completions",
            "Image generation (ImageFX/Whisk-like)",
            "Video generation (Flow/VideoFX-like)",
            "Multi-account load balancing",
            "Session persistence",
        ],
        "endpoints": {
            "docs": "/docs",
            "openai_api": "/v1/chat/completions",
            "image_studio": {
                "generate": "/v1/image/generate",
                "edit": "/v1/image/edit",
                "remix": "/v1/image/remix",
                "ingredients": "/v1/image/from-ingredients",
            },
            "video_studio": {
                "generate": "/v1/video/generate",
                "from_image": "/v1/video/from-image",
                "extend": "/v1/video/extend",
                "interpolate": "/v1/video/interpolate",
            },
            "health": "/v1/health",
        },
        "models": Config.SUPPORTED_MODELS,
    }


@app.get("/admin")
async def admin_redirect():
    """Redirect to admin UI"""
    return RedirectResponse(url="/static/index.html")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": str(exc),
                "type": type(exc).__name__,
            }
        },
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info",
    )
