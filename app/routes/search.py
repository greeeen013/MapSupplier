from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Supplier
import requests
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

GOOGLE_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

@router.get("/places")
def search_places(query: str, location: str = "Czech_Republic", db: Session = Depends(get_db)):
    """
    Search for places using Google Places Text Search API.
    Filters out already rejected suppliers.
    """
    if not GOOGLE_API_KEY:
        # Mock response for dev without API key
        if os.getenv("DEV_MODE") == "True":
             return [
                 {"google_id": "123", "name": "Mock Supplier 1", "rating": 4.5, "address": "Test Address 1", "status": "new", "images": []},
                 {"google_id": "456", "name": "Mock Supplier 2", "rating": 3.8, "address": "Test Address 2", "status": "new", "images": []}
             ]
        raise HTTPException(status_code=500, detail="Google Maps API Key not found. Please set GOOGLE_MAPS_API_KEY in .env")
    
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    full_query = f"{query} in {location}"
    params = {
        "query": full_query,
        "key": GOOGLE_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if data.get("status") not in ["OK", "ZERO_RESULTS"]:
         raise HTTPException(status_code=400, detail=f"Google API Error: {data.get('status')} - {data.get('error_message')}")

    results = []
    for place in data.get("results", []):
        google_id = place.get("place_id")
        
        # Check database for status
        existing = db.query(Supplier).filter(Supplier.google_id == google_id).first()
        status = "new"
        
        if existing:
            status = existing.status
            # If rejected or skipped forever, do not show in search results
            if status in ["rejected", "skipped_forever"]:
                continue
        
        location_coords = place.get("geometry", {}).get("location", {})
        lat = location_coords.get("lat")
        lng = location_coords.get("lng")
        
        photo_ref = place.get("photos", [{}])[0].get("photo_reference")
        image_url = None
        is_street_view = False
        
        if photo_ref:
            image_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_ref}&key={GOOGLE_API_KEY}"
        elif lat and lng:
            image_url = f"https://maps.googleapis.com/maps/api/streetview?size=400x400&location={lat},{lng}&key={GOOGLE_API_KEY}"
            is_street_view = True
            
        results.append({
            "google_id": google_id,
            "name": place.get("name"),
            "rating": place.get("rating"),
            "address": place.get("formatted_address"),
            "images": [image_url] if image_url else [],
            "status": status,
            "keyword_found": query, # Pass back to frontend to save later
            "is_street_view": is_street_view
        })
        
    return results

@router.get("/details")
def get_place_details(place_id: str):
    if not GOOGLE_API_KEY:
        if os.getenv("DEV_MODE") == "True":
             return {"formatted_phone_number": "123-456-789", "website": "http://example.com", "reviews": []}
        raise HTTPException(status_code=500, detail="Google Maps API Key not found")
        
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "name,rating,formatted_phone_number,website,formatted_address,photos,reviews",
        "key": GOOGLE_API_KEY
    }
    response = requests.get(url, params=params)
    return response.json().get("result")
