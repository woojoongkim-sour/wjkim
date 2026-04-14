from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class CustomerAlias(Base):
    __tablename__ = "customer_aliases"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    alias = Column(String(255), nullable=False)
    alias_type = Column(String(20), default="name")  # name | code | domain | email_pattern
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="aliases")

    __table_args__ = (
        UniqueConstraint('customer_id', 'alias', name='uix_customer_alias'),
    )


class EmailCustomerMapping(Base):
    __tablename__ = "email_customer_mappings"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    
    email_pattern = Column(String(255), nullable=False)  # exact email or domain pattern
    pattern_type = Column(String(20), default="exact")  # exact | domain | prefix
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer")

    __table_args__ = (
        UniqueConstraint('email_pattern', name='uix_email_pattern'),
    )
