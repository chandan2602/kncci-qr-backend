"""
Custom exceptions and error handlers for KNCCI API
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class KNCCIException(Exception):
    """Base exception for KNCCI API"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class DatabaseException(KNCCIException):
    """Database related exceptions"""
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, 503)

class EmailException(KNCCIException):
    """Email related exceptions"""
    def __init__(self, message: str = "Email operation failed"):
        super().__init__(message, 500)

class ValidationException(KNCCIException):
    """Validation related exceptions"""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, 400)

async def kncci_exception_handler(request: Request, exc: KNCCIException):
    """Handle custom KNCCI exceptions"""
    logger.error(f"KNCCI Exception: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.message,
            "type": exc.__class__.__name__
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "type": "InternalServerError"
        }
    )