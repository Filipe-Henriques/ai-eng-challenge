"""FastAPI application entry point for DEUS Bank AI Support System.

This module creates and configures the FastAPI application, wires up API routers,
and provides a development server entry point.
"""

from fastapi import FastAPI
import uvicorn

from app.api.v1.endpoints.chat import router

# Create FastAPI application
app = FastAPI(
    title="DEUS Bank AI Support",
    version="1.0.0",
)

# Include chat router
app.include_router(router, prefix="", tags=["chat"])


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Status information indicating the service is healthy
    """
    return {"status": "ok"}


if __name__ == "__main__":
    """Development server entry point.
    
    Run the FastAPI application using uvicorn with auto-reload enabled.
    Usage: python -m app.main
    """
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
