from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import Supplier
from ..schemas import SupplierCreate, SupplierResponse, SupplierBase
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

@router.post("/", response_model=SupplierResponse)
def create_or_update_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    """
    Add a supplier (Approve) or Reject/Skip (Store logic).
    Fetches additional details (Phone, Web, Email via scraping) if not present.
    """
    
    # Normalize tags to uppercase to avoid case duplicates
    if supplier.tags:
        supplier.tags = [t.upper() for t in supplier.tags]

    # Enrich data if status is accepted/new and we have a google_id
    if supplier.status in ["accepted"] and supplier.google_id:
        enrich_data(supplier)

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

def enrich_data(supplier: SupplierCreate):
    """
    Fetches phone/website from Google Place Details.
    If website found, tries to scrape email.
    Modifies the supplier object in-place.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key: return

    # 1. Fetch Details from Google
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": supplier.google_id,
            "fields": "formatted_phone_number,website,formatted_address,rating,user_ratings_total",
            "key": api_key
        }
        res = requests.get(url, params=params, timeout=5)
        data = res.json().get("result", {})
        
        if data.get("formatted_phone_number"):
            supplier.phone = data.get("formatted_phone_number")
        if data.get("website"):
            supplier.website = data.get("website")
        if data.get("formatted_address"): # Update address if detailed one is better
            supplier.address = data.get("formatted_address") 
        if data.get("user_ratings_total"):
             supplier.reviews_count = data.get("user_ratings_total")

    except Exception as e:
        print(f"Error fetching Google Details: {e}")

    # 2. Scrape Email from Website if we have one and no email yet
    if supplier.website and not supplier.email:
        print(f"Scraping {supplier.website} for email...")
        try:
            supplier.email = scrape_email(supplier.website)
            if supplier.email:
                print(f"FOUND EMAIL: {supplier.email}")
            else:
                print("No email found on website.")
        except Exception as e:
            print(f"Error scraping email: {e}")

def scrape_email(url: str) -> Optional[str]:
    import re
    from bs4 import BeautifulSoup
    
    try:
        # Simple timeout to avoid hanging
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        if resp.status_code != 200: return None
        
        text = resp.text
        soup = BeautifulSoup(text, 'html.parser')
        
        # Method A: Mailto links (High confidence)
        mailto = soup.select_one('a[href^=mailto]')
        if mailto:
            href = mailto.get('href')
            if href:
                # Remove 'mailto:' and params
                clean_email = href.replace('mailto:', '').split('?')[0]
                if '@' in clean_email:
                    return clean_email
        
        # Method B: Regex on text (Primitive, looking for @)
        # Regex for something@something.something
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
        if emails:
             # Filter out common false positives (images, etc)
             valid_emails = [e for e in emails if not e.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.js', '.css'))]
             if valid_emails:
                 return valid_emails[0]
                 
    except Exception as e:
        print(f"Scraper exception: {e}")
    return None

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
