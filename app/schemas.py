from pydantic import BaseModel, Field, EmailStr
from datetime import date, datetime
from typing import Optional


class OrderBase(BaseModel):
    first_name: str = Field(..., min_length=1, description="First name of the order")
    last_name: str = Field(..., min_length=1, description="Last name of the order")
    date_of_birth: date = Field(..., description="Date of birth")


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1)
    last_name: Optional[str] = Field(None, min_length=1)
    date_of_birth: Optional[date] = None


class Order(OrderBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Auth schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")


class UserLogin(BaseModel):
    username: str
    password: str


class User(UserBase):
    id: int
    created_at: datetime
    is_active: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Activity log schemas
class ActivityLogBase(BaseModel):
    method: str
    endpoint: str
    status_code: int
    request_body: Optional[str] = None
    response_body: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class ActivityLog(ActivityLogBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

