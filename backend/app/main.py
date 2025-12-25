"""
SmashForm Backend - FastAPI Application

Biomechanics-based badminton coaching platform.
Analyzes overhead smash technique from side-view video.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .api.routes import router as api_router

# Create FastAPI app
app = FastAPI(
    title="SmashForm API",
    description="Biomechanics analysis for badminton overhead smash technique",
    version="1.0.0",
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": "SmashForm",
        "version": "1.0.0",
        "description": "Biomechanics analysis for badminton smash technique"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "api": "operational",
            "pose_extraction": "ready",
            "biomechanics": "ready",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

