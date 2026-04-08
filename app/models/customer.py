from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.enums import ProtectionType, ProcessingStatus, ProcessingCapability, DocumentType
import uuid


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    documents = relationship("Document", back_populates="customer")
    servers = relationship("Server", back_populates="customer")
    services = relationship("Service", back_populates="customer")
    event_occurrences = relationship("EventOccurrence", back_populates="customer")
    incident_cases = relationship("IncidentCase", back_populates="customer")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    hostname = Column(String(255), nullable=False)
    ip_address = Column(String(45))
    os_type = Column(String(100))
    environment = Column(String(50))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="servers")
    documents = relationship("Document", secondary="document_server_association", back_populates="servers")
    services = relationship("Service", secondary="service_server_association", back_populates="servers")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    service_type = Column(String(100))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    customer = relationship("Customer", back_populates="services")
    servers = relationship("Server", secondary="service_server_association", back_populates="services")
    documents = relationship("Document", secondary="document_service_association", back_populates="services")
