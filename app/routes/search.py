from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Supplier
from ..scraper import advanced_scrape_emails
from ..logger import log
import requests
import os
import json
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

def get_ai_prompt(query: str, location: str) -> str:
    return f"""
    Najdi 5-10 dodavatelů/firem pro termín "{query}" v oblasti "{location}". 
    Vrať čistě JSON pole (array of objects), kde každý objekt má exaktně tyto klíče:
    - "name": Přesný název firmy
    - "address": Celá adresa firmy
    - "email": Firemní e-mail (odhadni nebo najdi, null pokud neznáš)
    Nevypisuj žádný jiný text, pouze surový JSON.
    """

@router.get("/ai_prompt_text")
def ai_prompt_text(query: str = "Tvé slovo", location: str = "Tvá oblast"):
    """Returns the raw prompt used for AI."""
    return {"prompt": get_ai_prompt(query, location)}

@router.get("/ai_raw")
def ai_raw_response(query: str, location: str = "Czech_Republic"):
    """Returns raw, unparsed string directly from Gemini for debugging."""
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API Key missing")
        
    prompt = get_ai_prompt(query, location)
    log.info(f"AI RAW Debug spuštěn pro query: {query}, loc: {location}")
    
    try:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
            )
            raw_text = response.text
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-pro')
            response = model.generate_content(prompt)
            raw_text = response.text
            
        return {"prompt": prompt, "raw_response": raw_text}
    except Exception as e:
        log.error(f"Chyba při volání AI api v AI RAW: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai_places")
def ai_search_places(query: str, location: str = "Czech_Republic", db: Session = Depends(get_db)):
    """
    Search for places using Gemini API.
    Returns custom cards based on AI generation + deep scrapes websites.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API Key not found. Please set GEMINI_API_KEY in .env")

    prompt = get_ai_prompt(query, location)
    log.info(f"Hledám přes AI: {query} v oblasti {location}")

    try:
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
            )
            raw_text = response.text
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-2.5-pro')
            response = model.generate_content(prompt)
            raw_text = response.text
        
        log.info(f"Google Gemini odpovědělo úspěšně ({len(raw_text)} znaků).")
        
        # Clean markdown code block formatting if present
        raw_text = raw_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        suppliers_data = json.loads(raw_text.strip())
        log.info(f"AI vygenerovalo {len(suppliers_data)} potenciálních firem.")
        
        results = []
        for index, item in enumerate(suppliers_data):
            company_name = item.get("name", "")
            company_address = item.get("address", "")
            
            log.info(f"Zpracovávám firmu z AI: {company_name}")
            fallback_id = f"ai_{index}"
            
            real_google_id = None
            resolved_website = None
            resolved_phone = None
            resolved_rating = None
            resolved_address = company_address
            
            if GOOGLE_API_KEY and company_name:
                search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                gmap_params = {"query": f"{company_name} {company_address}", "key": GOOGLE_API_KEY}
                try:
                    gmap_res = requests.get(search_url, params=gmap_params).json()
                    if gmap_res.get("status") == "OK" and len(gmap_res.get("results", [])) > 0:
                        first_result = gmap_res["results"][0]
                        real_google_id = first_result.get("place_id")
                        resolved_address = first_result.get("formatted_address", company_address)
                        resolved_rating = first_result.get("rating")
                        
                        # Get Details for website/phone
                        details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                        det_params = {"place_id": real_google_id, "fields": "website,formatted_phone_number", "key": GOOGLE_API_KEY}
                        det_res = requests.get(details_url, params=det_params).json()
                        if det_res.get("status") == "OK":
                            resolved_website = det_res["result"].get("website")
                            resolved_phone = det_res["result"].get("formatted_phone_number")
                            if resolved_website:
                                log.info(f" -> Nalezen Web: {resolved_website}")
                except Exception as map_e:
                    log.error(f"Maps API selhalo pro '{company_name}': {map_e}")
                    print(f"Maps resolution failed for {company_name}: {map_e}")

            pseudo_id = real_google_id or f"ai_hash_{hash(company_name + resolved_address)}"
            
            # Check database for status
            existing = db.query(Supplier).filter(Supplier.google_id == pseudo_id).first()
            status = "new"
            if existing:
                status = existing.status
                if status in ["rejected", "skipped_forever"]:
                    continue
                    
            # Deep Scrape Emails if website found
            scraped_emails_data = {"emails": []}
            if resolved_website:
                scraped_emails_data = advanced_scrape_emails(resolved_website)
                
            scraped_emails = scraped_emails_data.get("emails", [])
            ai_email = item.get("email")

            # Merge and verify emails
            final_emails_list = []
            seen_email_addresses = set()
            
            if scraped_emails:
                # 1. Add Scraped (Verified) emails
                for em in scraped_emails:
                    if em and isinstance(em, str):
                        em_lower = em.strip().lower()
                        if em_lower not in seen_email_addresses:
                            final_emails_list.append({"address": em_lower, "verified": True})
                            seen_email_addresses.add(em_lower)
            else:
                # 2. Add AI (Unverified) email if no web emails found
                if ai_email and isinstance(ai_email, str):
                    ai_em_lower = ai_email.strip().lower()
                    final_emails_list.append({"address": ai_em_lower, "verified": False})
                
            results.append({
                "google_id": pseudo_id,
                "name": company_name or "Neznámý název",
                "emails_rich": final_emails_list, # New structure for frontend
                "address": resolved_address,
                "phone": resolved_phone,
                "website": resolved_website,
                "rating": resolved_rating,
                "images": [],
                "status": status,
                "keyword_found": query,
                "is_street_view": False,
                "tags": ["AI search", query, location]
            })
            
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Search error: {str(e)}")
