import json
import logging
import re
from typing import Optional
from fastapi import Request
from fastapi.responses import Response, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import SessionLocal
from app.activity_logger import log_activity, get_client_ip, get_user_agent
from app import models
from jose import JWTError, jwt
from app.auth import SECRET_KEY

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log all API requests"""
    
    # Endpoints to skip logging (health checks, docs, etc.)
    SKIP_PATHS = ["/health", "/docs", "/openapi.json", "/redoc", "/"]
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for certain paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)
        
        # Get user ID (try to authenticate, but don't fail if not authenticated)
        user_id = await self._get_user_id_safe(request)
        
        # Capture request body for non-GET requests
        # We'll cache the body and restore it so the endpoint can use it
        request_body = None
        body_cache = None
        
        if request.method != "GET":
            try:
                body_cache = await request.body()
                # Restore body for endpoint
                async def receive():
                    return {"type": "http.request", "body": body_cache}
                request._receive = receive
                
                # Now extract info from cached body
                request_body = self._extract_request_info(body_cache, request.headers.get("content-type", ""))
            except Exception as e:
                logger.debug(f"Could not capture request body: {str(e)}")
        
        # Process the request
        response = await call_next(request)
        
        # Capture response body
        response_body = await self._capture_response_body(response)
        
        # Log the activity
        await self._log_activity(
            request=request,
            response=response,
            user_id=user_id,
            request_body=request_body,
            response_body=response_body
        )
        
        return response
    
    async def _get_user_id_safe(self, request: Request) -> Optional[int]:
        """Try to get user ID from token, return None if not authenticated"""
        try:
            # Try to get token from Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None
            
            token = authorization.split(" ")[1]
            
            # Decode token
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                username = payload.get("sub")
                if not username:
                    return None
            except JWTError:
                return None
            
            # Get user from database
            db = SessionLocal()
            try:
                user = db.query(models.User).filter(models.User.username == username).first()
                if user and user.is_active == "true":
                    return user.id
                return None
            finally:
                db.close()
                
        except Exception as e:
            logger.debug(f"Could not get user ID from request: {str(e)}")
            return None
    
    def _extract_request_info(self, body: bytes, content_type: str) -> Optional[str]:
        """Extract request information from body bytes"""
        if not body:
            return None
        
        if "multipart/form-data" in content_type:
            # Try to extract filename from multipart form data
            try:
                # Search for filename= pattern in bytes
                # Pattern: filename="example.pdf" or filename=example.pdf
                pattern = rb'filename[=:]\s*["\']?([^"\'\r\n]+)["\']?'
                matches = re.findall(pattern, body, re.IGNORECASE)
                if matches:
                    try:
                        filename = matches[0].decode('utf-8', errors='ignore').strip()
                        # Clean up filename (remove path if present, remove quotes)
                        filename = filename.strip('"\'')
                        filename = filename.split('\\')[-1].split('/')[-1]
                        return f"File upload: {filename}"
                    except:
                        pass
                
                return "File upload (multipart/form-data)"
            except Exception as e:
                logger.debug(f"Could not extract filename from multipart data: {str(e)}")
                return "File upload (multipart/form-data)"
        
        # Try to parse as JSON
        try:
            return json.dumps(json.loads(body.decode()))[:1000]  # Limit length
        except:
            try:
                return body.decode()[:1000]  # Limit length
            except:
                return None
    
    async def _capture_response_body(self, response: Response) -> Optional[str]:
        """Capture response body for logging"""
        try:
            # For StreamingResponse or responses with body iterator
            if isinstance(response, StreamingResponse):
                return None  # Can't easily capture streaming responses
            
            # Try to get body from response
            if hasattr(response, 'body'):
                body = response.body
                if isinstance(body, bytes):
                    try:
                        body_str = body.decode()
                        return json.dumps(json.loads(body_str))[:1000] if body_str else None
                    except:
                        return body.decode()[:1000] if body else None
                return str(body)[:1000] if body else None
            
            return None
        except Exception:
            return None
    
    async def _log_activity(
        self,
        request: Request,
        response: Response,
        user_id: Optional[int],
        request_body: Optional[str],
        response_body: Optional[str]
    ):
        """Log the activity to database"""
        # Log all requests, even unauthenticated ones (user_id will be None)
        db = SessionLocal()
        try:
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
        except Exception as e:
            logger.error(f"Failed to log activity in middleware: {str(e)}", exc_info=True)
        finally:
            db.close()

