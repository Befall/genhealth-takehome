import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app import crud, schemas
from app.database import SessionLocal
from app.pdf_extractor import extract_order_info_from_pdf
from app.auth import get_current_user
from app import models
from app.exceptions import FileValidationError, PDFExtractionError, DatabaseError

logger = logging.getLogger(__name__)

# File size limits (10MB max)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

router = APIRouter(prefix="/order", tags=["order"])


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new order from a PDF file"""
    # Validate file was provided
    if not file.filename:
        raise FileValidationError("No file provided. Please upload a PDF file.")
    
    # Validate file type by extension
    if not file.filename.lower().endswith('.pdf'):
        raise FileValidationError(
            f"Invalid file type. Expected PDF, got: {file.filename.split('.')[-1] if '.' in file.filename else 'unknown'}"
        )
    
    # Validate file size
    try:
        # Read file content to check size
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > MAX_FILE_SIZE:
            raise FileValidationError(
                f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f}MB, "
                f"got {file_size / (1024*1024):.2f}MB"
            )
        
        if file_size == 0:
            raise FileValidationError("File is empty. Please upload a valid PDF file.")
        
        # Reset file pointer for processing
        await file.seek(0)
        
        # Validate it's actually a PDF by checking magic bytes
        if not file_content.startswith(b'%PDF'):
            raise FileValidationError(
                "File does not appear to be a valid PDF. Please check the file and try again."
            )
        
        # Reset again after validation
        await file.seek(0)
        
    except FileValidationError:
        raise
    except Exception as e:
        logger.error(f"Error validating file: {str(e)}", exc_info=True)
        raise FileValidationError("Error reading file. Please ensure the file is valid and try again.")
    
    # Extract information from PDF
    try:
        first_name, last_name, date_of_birth = extract_order_info_from_pdf(file)
    except HTTPException:
        # Re-raise HTTPExceptions from PDF extraction (they're already formatted)
        raise
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}", exc_info=True)
        raise PDFExtractionError(
            "Failed to extract patient information from PDF. "
            "Please ensure the PDF contains patient name and date of birth in a readable format."
        )
    
    # Validate extracted data
    if not first_name or len(first_name.strip()) == 0:
        raise FileValidationError("Extracted first name is empty. Please check the PDF format.")
    if not last_name or len(last_name.strip()) == 0:
        raise FileValidationError("Extracted last name is empty. Please check the PDF format.")
    if len(first_name) > 100 or len(last_name) > 100:
        raise FileValidationError("Extracted name is too long. Please check the PDF format.")
    
    # Sanitize names (remove extra whitespace, limit length)
    first_name = first_name.strip()[:100]
    last_name = last_name.strip()[:100]
    
    # Create order schema
    try:
        order = schemas.OrderCreate(
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth
        )
    except Exception as e:
        logger.error(f"Error creating order schema: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order data. Please check the extracted information."
        )
    
    # Save to database
    try:
        order_result = crud.create_order(db=db, order=order, user_id=current_user.id)
    except SQLAlchemyError as e:
        logger.error(f"Database error creating order: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to save order to database. Please try again later.")
    except Exception as e:
        logger.error(f"Unexpected error creating order: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the order."
        )
    
    return order_result


@router.get("/", response_model=List[schemas.Order])
async def read_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all orders"""
    orders = crud.get_orders(db, skip=skip, limit=limit)
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
async def read_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific order by ID"""
    db_order = crud.get_order(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    return db_order


@router.put("/{order_id}", response_model=schemas.Order)
async def update_order(
    order_id: int,
    order_update: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update an existing order"""
    try:
        db_order = crud.update_order(db, order_id=order_id, order_update=order_update)
    except SQLAlchemyError as e:
        logger.error(f"Database error updating order {order_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to update order. Please try again later.")
    
    if db_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    return db_order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete an order"""
    try:
        success = crud.delete_order(db, order_id=order_id)
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting order {order_id}: {str(e)}", exc_info=True)
        db.rollback()
        raise DatabaseError("Failed to delete order. Please try again later.")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    return None

