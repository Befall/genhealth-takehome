from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import verify_password, get_password_hash


def get_user_by_username(db: Session, username: str):
    """Get a user by username"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str):
    """Get a user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user(db: Session, user_id: int):
    """Get a user by ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user"""
    # Check if username already exists
    if get_user_by_username(db, user.username):
        raise ValueError("Username already registered")
    
    # Check if email already exists
    if get_user_by_email(db, user.email):
        raise ValueError("Email already registered")
    
    # Ensure password is a string
    password = str(user.password) if user.password else ""
    hashed_password = get_password_hash(password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by username and password"""
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    if user.is_active != "true":
        return False
    return user

