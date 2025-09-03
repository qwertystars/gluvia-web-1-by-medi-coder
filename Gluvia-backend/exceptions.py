# exceptions.py
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class GluviaException(Exception):
    """Base exception for Gluvia application"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(GluviaException):
    """Raised when data validation fails"""
    pass

class PrescriptionNotFoundError(GluviaException):
    """Raised when prescription is not found"""
    pass

class DoseTooHighError(GluviaException):
    """Raised when insulin dose is dangerously high"""
    pass

class InsulinTypeError(GluviaException):
    """Raised when insulin type is invalid"""
    pass

def create_http_exception(
    status_code: int,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """Create standardized HTTP exception"""
    return HTTPException(
        status_code=status_code,
        detail={
            "error": True,
            "message": message,
            "details": details or {},
            "timestamp": str(datetime.now(timezone.utc))
        }
    )

# Common HTTP exceptions
def validation_exception(message: str, details: Optional[Dict] = None):
    return create_http_exception(status.HTTP_400_BAD_REQUEST, message, details)

def not_found_exception(message: str, details: Optional[Dict] = None):
    return create_http_exception(status.HTTP_404_NOT_FOUND, message, details)

def unauthorized_exception(message: str = "Authentication required"):
    return create_http_exception(status.HTTP_401_UNAUTHORIZED, message)

def forbidden_exception(message: str = "Access forbidden"):
    return create_http_exception(status.HTTP_403_FORBIDDEN, message)

def internal_server_exception(message: str = "Internal server error"):
    logger.error(f"Internal server error: {message}")
    return create_http_exception(status.HTTP_500_INTERNAL_SERVER_ERROR, message)
