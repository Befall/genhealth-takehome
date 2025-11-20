from sqlalchemy.orm import Session
from app import models, schemas
from typing import List, Optional


def get_order(db: Session, order_id: int) -> Optional[models.Order]:
    """Get a single order by ID"""
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def get_orders(db: Session, skip: int = 0, limit: int = 100) -> List[models.Order]:
    """Get all orders with pagination"""
    return db.query(models.Order).offset(skip).limit(limit).all()


def create_order(db: Session, order: schemas.OrderCreate, user_id: Optional[int] = None) -> models.Order:
    """Create a new order"""
    db_order = models.Order(
        first_name=order.first_name,
        last_name=order.last_name,
        date_of_birth=order.date_of_birth,
        created_by_user_id=user_id
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order


def update_order(
    db: Session, order_id: int, order_update: schemas.OrderUpdate
) -> Optional[models.Order]:
    """Update an existing order"""
    db_order = get_order(db, order_id)
    if not db_order:
        return None
    
    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    
    db.commit()
    db.refresh(db_order)
    return db_order


def delete_order(db: Session, order_id: int) -> bool:
    """Delete an order by ID"""
    db_order = get_order(db, order_id)
    if not db_order:
        return False
    
    db.delete(db_order)
    db.commit()
    return True

