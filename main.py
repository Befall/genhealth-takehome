# Load environment variables from .env file FIRST, before any other imports
from dotenv import load_dotenv
load_dotenv()

# Now import everything else
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.database import engine, Base
from app.routers import orders, auth
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Order Management API",
    description="REST API for managing orders with CRUD operations",
    version="1.0.0"
)

# Add activity logging middleware
from app.middleware import ActivityLoggingMiddleware
app.add_middleware(ActivityLoggingMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(orders.router)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        message = error.get("msg", "Validation error")
        error_messages.append(f"{field}: {message}")
    
    logger.warning(f"Validation error on {request.url.path}: {error_messages}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": error_messages,
            "message": "Validation error. Please check your request data."
        }
    )


from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions (404, etc.)"""
    if exc.status_code == 404:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Endpoint not found: {request.url.path}",
                "message": "The requested resource was not found."
            }
        )
    # For other HTTP exceptions, return as-is
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            "message": "Request error"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    # Log the full exception with traceback
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=True
    )
    
    # Check if it's a database error
    if isinstance(exc, SQLAlchemyError):
        logger.error(f"Database error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "A database error occurred. Please try again later.",
                "message": "Internal server error"
            }
        )
    
    # For production, don't expose internal error details
    # In development, you might want to show more details
    import os
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred. Please try again later." if is_production else str(exc),
            "message": "Internal server error"
        }
    )


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Order Management API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/routes")
def list_routes():
    return [route.path for route in app.router.routes]
