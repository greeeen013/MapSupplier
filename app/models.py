from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, Float
from sqlalchemy.sql import func
from .database import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    rating = Column(Float, nullable=True)
    keyword = Column(String, nullable=True) # Search term used to find this
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    website = Column(String, nullable=True)
    images = Column(JSON, nullable=True) # List of image URLs
    reviews_count = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    tags = Column(JSON, nullable=True) # E.g. ["AI search", keyword, country]
    country = Column(String, nullable=True)
    source = Column(String, nullable=True)  # How the supplier was found: 'AI SEARCH', 'GOOGLE MAPS', etc.

    status = Column(String, default="pending") # pending, accepted, rejected, contacted, skipped_forever
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailPreset(Base):
    __tablename__ = "email_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    subject = Column(String, default="")
    body = Column(Text, default="")
    preset_type = Column(String, default="template") # 'template' or 'ai_prompt'
