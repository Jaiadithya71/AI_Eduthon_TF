from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="AI-Powered Personalized Presentation Generation Platform for Educators",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


# ----------------------------------------------------
# 🔥 UNIVERSAL STARTUP LOGS (WORKS FOR UVICORN CLI TOO)
# ----------------------------------------------------
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting EduSlide AI v1.0.0")
    print(f"📝 Environment: {settings.ENVIRONMENT}")
    print(f"🔗 API Docs: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs")
    print(f"✅ Groq AI: {'Configured' if settings.GROQ_API_KEY else 'Missing'}")
    print(f"🖼️  Pexels: {'Configured' if settings.PEXELS_API_KEY else 'Using placeholders'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("👋 Shutting down EduSlide AI API")


# ----------------------------------------------------
# 🔥 DIRECT PYTHON RUN SUPPORT (OPTIONAL)
# ----------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG
    )
