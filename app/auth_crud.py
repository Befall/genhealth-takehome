import re
import os
from pathlib import Path
from sqlalchemy.orm import Session
from app import models, schemas
from app.auth import verify_password, get_password_hash

# Load common passwords from file (cached at module level)
_COMMON_PASSWORDS = None


def _load_common_passwords() -> set:
    """Load common passwords from file into a set for fast lookup"""
    global _COMMON_PASSWORDS
    if _COMMON_PASSWORDS is None:
        # Get the path to the common_passwords.txt file
        current_dir = Path(__file__).parent
        passwords_file = current_dir / "common_passwords.txt"
        
        _COMMON_PASSWORDS = set()
        try:
            with open(passwords_file, 'r', encoding='utf-8') as f:
                for line in f:
                    password = line.strip()
                    if password:  # Skip empty lines
                        _COMMON_PASSWORDS.add(password.lower())
        except FileNotFoundError:
            # Fallback to a small list if file not found
            _COMMON_PASSWORDS = {"password", "12345678", "qwerty", "abc123", "password123"}
    
    return _COMMON_PASSWORDS


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check against list of 10,000 most common passwords
    common_passwords = _load_common_passwords()
    if password.lower() in common_passwords:
        return False, "Password is too common. Please choose a stronger password."
    
    # Optional: Check for basic complexity (at least one letter and one number)
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, ""


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
    """Create a new user with password validation"""
    # Check if username already exists
    if get_user_by_username(db, user.username):
        raise ValueError("Username already registered")
    
    # Check if email already exists
    if get_user_by_email(db, user.email):
        raise ValueError("Email already registered")
    
    # Validate password strength
    password = str(user.password) if user.password else ""
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_message)
    
    # Hash password
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

