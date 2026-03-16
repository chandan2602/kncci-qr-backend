from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import asyncio

from config import settings
from database import Base, engine, test_db_connection
from routers import registration, applications, payment
from routers import Holland_code as holland
from utils.logger import logger
from utils.exceptions import (
    KNCCIException, 
    kncci_exception_handler, 
    general_exception_handler
)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)

# Add exception handlers
app.add_exception_handler(KNCCIException, kncci_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(registration.router)
app.include_router(applications.router)
app.include_router(payment.router)
app.include_router(holland.router)

@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Test database connection
    if test_db_connection():
        logger.info("Database connection successful")
    
    # Initialize Holland Code services
    try:
        await holland.init_db_pool()
        holland.load_initial_data()
        logger.info("Holland Code services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Holland Code services: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down KNCCI API")
    
    # Close Holland Code database pool
    if holland.db_pool:
        await holland.db_pool.close()
        logger.info("Holland Code DB connection pool closed")
    else:
        logger.error("Database connection failed")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    logger.info("Shutting down KNCCI API")

@app.get("/")
async def root():
    return {
        "message": "KNCCI QR Form API is running",
        "version": settings.app_version,
        "status": "healthy"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint with database connection test"""
    try:
        db_status = test_db_connection()
        return {
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected",
            "version": settings.app_version,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "error",
            "error": str(e),
            "version": settings.app_version,
            "timestamp": datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(app, host=settings.host, port=settings.port)