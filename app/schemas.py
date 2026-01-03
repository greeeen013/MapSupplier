from pydantic import BaseModel
from typing import List, Optional

class SupplierBase(BaseModel):
    google_id: str
    name: str
    rating: Optional[float] = None
    keyword: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    images: Optional[List[str]] = None
    reviews_count: Optional[int] = None
    description: Optional[str] = None

class SupplierCreate(SupplierBase):
    status: str = "accepted" # accepted or rejected
    rejection_reason: Optional[str] = None

class SupplierResponse(SupplierBase):
    id: int
    status: str
    class Config:
        from_attributes = True

class EmailPresetCreate(BaseModel):
    name: str
    subject: str
    body: str

class EmailPresetResponse(EmailPresetCreate):
    id: int
    class Config:
        from_attributes = True
