from fastapi import Request
from sqlalchemy.orm import Session
from app import models
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


def log_activity(
    user_id: int = None,
    method: str = None,
    endpoint: str = None,
    status_code: int = None,
    request_body: str = None,
    response_body: str = None,
    ip_address: str = None,
    user_agent: str = None,
    db: Session = None
):
    """Log user activity to the database"""
    if db is None:
        db = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        activity_log = models.ActivityLog(
            user_id=user_id,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            request_body=request_body,
            response_body=response_body,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(activity_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log activity: {str(e)}", exc_info=True)
        db.rollback()
    finally:
        if should_close:
            db.close()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> str:
    """Get user agent from request"""
    return request.headers.get("user-agent")


