from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CustomerBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    description: Optional[str] = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ServerBase(BaseModel):
    hostname: str = Field(..., max_length=255)
    ip_address: Optional[str] = Field(None, max_length=45)
    os_type: Optional[str] = Field(None, max_length=100)
    environment: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class ServerCreate(ServerBase):
    customer_id: int


class ServerUpdate(BaseModel):
    hostname: Optional[str] = Field(None, max_length=255)
    ip_address: Optional[str] = Field(None, max_length=45)
    os_type: Optional[str] = Field(None, max_length=100)
    environment: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ServerResponse(ServerBase):
    id: int
    customer_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceBase(BaseModel):
    name: str = Field(..., max_length=255)
    service_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None


class ServiceCreate(ServiceBase):
    customer_id: int


class ServiceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    service_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: int
    customer_id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
