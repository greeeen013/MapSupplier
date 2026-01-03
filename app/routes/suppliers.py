from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import Supplier
from ..schemas import SupplierCreate, SupplierResponse, SupplierBase

router = APIRouter()

@router.post("/", response_model=SupplierResponse)
def create_or_update_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    """
    Add a supplier (Approve) or Reject/Skip (Store logic).
    If it exists (e.g. was rejected but now approved), update it.
    """
    db_supplier = db.query(Supplier).filter(Supplier.google_id == supplier.google_id).first()
    
    if db_supplier:
        for key, value in supplier.dict().items():
            setattr(db_supplier, key, value)
        db.commit()
        db.refresh(db_supplier)
        return db_supplier
    
    new_supplier = Supplier(**supplier.dict())
    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier

@router.get("/", response_model=List[SupplierResponse])
def get_suppliers(status: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Supplier)
    if status:
        query = query.filter(Supplier.status == status)
    return query.order_by(Supplier.created_at.desc()).offset(skip).limit(limit).all()

@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, supplier: SupplierCreate, db: Session = Depends(get_db)):
    db_supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    for key, value in supplier.dict(exclude_unset=True).items():
        setattr(db_supplier, key, value)
    
    db.commit()
    db.refresh(db_supplier)
    return db_supplier
