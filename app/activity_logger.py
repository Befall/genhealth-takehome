import json
from fastapi import Request, Response
from sqlalchemy.orm import Session
from app import models
from app.database import SessionLocal
import logging

logger = logging.getLogger(__name__)


def log_activity(
    user_id: int,
    method: str,
    endpoint: str,
    status_code: int,
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


async def log_request_response(
    request: Request,
    response: Response,
    user_id: int,
    db: Session,
    response_body_str: str = None
):
    """Log the request and response"""
    # Get request body if available (for non-GET requests)
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            # For file uploads, we can't read the body again, so skip it
            if "multipart/form-data" not in request.headers.get("content-type", ""):
                body = await request.body()
                if body:
                    # Try to parse as JSON
                    try:
                        request_body = json.dumps(json.loads(body.decode()))
                    except:
                        request_body = body.decode()[:1000]  # Limit length
        except:
            pass
    
    # Use provided response body or try to get it from response
    response_body = response_body_str
    if response_body is None:
        try:
            if hasattr(response, 'body'):
                body_str = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
                response_body = body_str[:1000] if body_str else None  # Limit length
        except:
            pass
    
    # Log the activity
    log_activity(
        user_id=user_id,
        method=request.method,
        endpoint=str(request.url.path),
        status_code=response.status_code,
        request_body=request_body,
        response_body=response_body,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        db=db
    )

