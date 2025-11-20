from fastapi import FastAPI
from app.database import engine, Base
from app.routers import orders
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Order Management API",
    description="REST API for managing orders with CRUD operations",
    version="1.0.0"
)

# Include routers
app.include_router(orders.router)


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

