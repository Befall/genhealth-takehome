from pydantic import BaseModel, Field
from datetime import date
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

    class Config:
        from_attributes = True

