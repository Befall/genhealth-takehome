from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request, Response
from sqlalchemy.orm import Session
from typing import List
from app import crud, schemas
from app.database import SessionLocal
from app.pdf_extractor import extract_order_info_from_pdf
from app.auth import get_current_user
from app import models
from app.activity_logger import log_activity, get_client_ip, get_user_agent

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
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new order from a PDF file"""
    # Validate file was provided
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF"
        )
    
    # Extract information from PDF
    first_name, last_name, date_of_birth = extract_order_info_from_pdf(file)
    
    # Create order schema
    order = schemas.OrderCreate(
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth
    )
    
    # Save to database
    order_result = crud.create_order(db=db, order=order, user_id=current_user.id)
    
    # Set response status code
    response.status_code = status.HTTP_201_CREATED
    
    # Log activity (convert response to string for logging)
    import json
    response_body = json.dumps({
        "id": order_result.id,
        "first_name": order_result.first_name,
        "last_name": order_result.last_name,
        "date_of_birth": str(order_result.date_of_birth)
    })
    
    # Log activity - note file uploads, so request body will be None
    log_activity(
        user_id=current_user.id,
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        request_body=f"File upload: {file.filename}" if file.filename else None,
        response_body=response_body,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db
    )
    
    return order_result


@router.get("/", response_model=List[schemas.Order])
async def read_orders(
    request: Request,
    response: Response,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all orders"""
    orders = crud.get_orders(db, skip=skip, limit=limit)
    response.status_code = status.HTTP_200_OK
    
    # Log activity
    import json
    response_body = json.dumps([{
        "id": o.id,
        "first_name": o.first_name,
        "last_name": o.last_name,
        "date_of_birth": str(o.date_of_birth)
    } for o in orders])
    
    log_activity(
        user_id=current_user.id,
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        request_body=None,
        response_body=response_body,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db
    )
    
    return orders


@router.get("/{order_id}", response_model=schemas.Order)
async def read_order(
    request: Request,
    response: Response,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get a specific order by ID"""
    db_order = crud.get_order(db, order_id=order_id)
    if db_order is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        log_activity(
            user_id=current_user.id,
            method=request.method,
            endpoint=str(request.url.path),
            status_code=status.HTTP_404_NOT_FOUND,
            request_body=None,
            response_body=None,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    response.status_code = status.HTTP_200_OK
    
    # Log activity
    import json
    response_body = json.dumps({
        "id": db_order.id,
        "first_name": db_order.first_name,
        "last_name": db_order.last_name,
        "date_of_birth": str(db_order.date_of_birth)
    })
    
    log_activity(
        user_id=current_user.id,
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        request_body=None,
        response_body=response_body,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db
    )
    
    return db_order


@router.put("/{order_id}", response_model=schemas.Order)
async def update_order(
    request: Request,
    response: Response,
    order_id: int,
    order_update: schemas.OrderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update an existing order"""
    db_order = crud.update_order(db, order_id=order_id, order_update=order_update)
    if db_order is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        log_activity(
            user_id=current_user.id,
            method=request.method,
            endpoint=str(request.url.path),
            status_code=status.HTTP_404_NOT_FOUND,
            request_body=None,
            response_body=None,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    response.status_code = status.HTTP_200_OK
    
    # Log activity
    import json
    response_body = json.dumps({
        "id": db_order.id,
        "first_name": db_order.first_name,
        "last_name": db_order.last_name,
        "date_of_birth": str(db_order.date_of_birth)
    })
    
    log_activity(
        user_id=current_user.id,
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        request_body=json.dumps(order_update.model_dump()),
        response_body=response_body,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db
    )
    
    return db_order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    request: Request,
    response: Response,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete an order"""
    success = crud.delete_order(db, order_id=order_id)
    if not success:
        response.status_code = status.HTTP_404_NOT_FOUND
        log_activity(
            user_id=current_user.id,
            method=request.method,
            endpoint=str(request.url.path),
            status_code=status.HTTP_404_NOT_FOUND,
            request_body=None,
            response_body=None,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    response.status_code = status.HTTP_204_NO_CONTENT
    
    # Log activity
    log_activity(
        user_id=current_user.id,
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        request_body=None,
        response_body=None,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db
    )
    
    return None

