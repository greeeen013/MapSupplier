from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Supplier
from ..logger import log
import json
import hashlib
import os
import re
import requests as http_requests

router = APIRouter()

DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'hikvision_data.json')

_data_cache = None


def _load_data():
    global _data_cache
    if _data_cache is not None:
        return _data_cache
    try:
        with open(DATA_FILE, encoding='utf-8') as f:
            _data_cache = json.load(f)
        log.info(f"Hikvision data načtena: {len(_data_cache.get('suppliers', []))} dodavatelů")
    except Exception as e:
        log.error(f"Nelze načíst hikvision_data.json: {e}")
        raise HTTPException(status_code=500, detail=f"Data soubor nenalezen: {e}")
    return _data_cache


DAHUA_CEEN_BASE = "https://www.dahuasecurity.com/ceen/partners/DistributionPartner"
DAHUA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_dahua_nuxt(html: str) -> dict:
    match = re.search(r'window\.__NUXT__\s*=\s*', html)
    if not match:
        raise ValueError("__NUXT__ not found in page")
    json_str = html[match.end():]
    end = json_str.find('</script>')
    if end == -1:
        raise ValueError("</script> not found after __NUXT__")
    data = json.loads(json_str[:end].rstrip('; \n\r'))
    return data["state"]["partner"]["distributionPartner"]["data"]


@router.get("/sources")
def get_sources():
    return [
        {"id": "hikvision", "name": "Hikvision", "available": True},
        {"id": "axis", "name": "Axis", "available": False},
        {"id": "dahua", "name": "Dahua", "available": True},
    ]


@router.get("/hikvision/regions")
def get_hikvision_regions():
    data = _load_data()
    return data.get("regions", {})


@router.get("/hikvision/stream")
def hikvision_stream(
    country_code: str = Query(...),
    country_name: str = Query(...),
    db: Session = Depends(get_db),
):
    def _event(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        yield _event({"type": "status", "message": f"Hledám dodavatele pro {country_name}..."})

        try:
            data = _load_data()
        except Exception as e:
            yield _event({"type": "error", "message": str(e)})
            return

        items = [s for s in data.get("suppliers", []) if s.get("country") == country_code]
        total = len(items)

        if total == 0:
            yield _event({"type": "done", "total": 0})
            return

        yield _event({"type": "total", "total": total})

        count = 0
        for item in items:
            name = item.get("name", "").strip()
            if not name:
                continue

            address = item.get("address", "")
            pseudo_id = f"hikvision_{hashlib.md5((name + address).encode()).hexdigest()[:12]}"

            existing = db.query(Supplier).filter(Supplier.google_id == pseudo_id).first()
            status = "new"
            if existing:
                status = existing.status
                if status in ["rejected", "skipped_forever"]:
                    continue

            logo = item.get("logo")
            supplier = {
                "google_id": pseudo_id,
                "name": name,
                "phone": item.get("phone", ""),
                "email": item.get("email", ""),
                "website": item.get("website", ""),
                "address": address,
                "description": item.get("description", ""),
                "images": [logo] if logo else [],
                "rating": None,
                "reviews_count": None,
                "status": status,
                "country": country_name,
                "source": "WEB SEARCH",
                "tag_source_search": "WEB SEARCH",
                "tag_keyword": "HIKVISION",
                "tag_location": country_name.upper(),
                "keyword": "HIKVISION",
            }

            yield _event({"type": "supplier", "data": supplier})
            count += 1

        yield _event({"type": "done", "total": count})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/dahua/countries")
def get_dahua_countries():
    """Returns CEEN country list scraped live from Dahua website."""
    try:
        resp = http_requests.get(f"{DAHUA_CEEN_BASE}?id=7", headers=DAHUA_HEADERS, timeout=15)
        resp.raise_for_status()
        data = _parse_dahua_nuxt(resp.text)
        return [c for c in data.get("menuList", []) if c["menu_id"] != "all"]
    except Exception as e:
        log.error(f"Dahua countries fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dahua/stream")
def dahua_stream(
    country_id: str = Query(...),
    country_name: str = Query(...),
    db: Session = Depends(get_db),
):
    def _event(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def generate():
        yield _event({"type": "status", "message": f"Načítám partnery pro {country_name}..."})
        try:
            resp = http_requests.get(
                f"{DAHUA_CEEN_BASE}?id={country_id}&child=all&page=1",
                headers=DAHUA_HEADERS, timeout=15,
            )
            resp.raise_for_status()
            data = _parse_dahua_nuxt(resp.text)

            total_count = int(data.get("count", 0))
            perpage = int(data.get("perpage", 12))
            total_pages = max(1, (total_count + perpage - 1) // perpage)

            yield _event({"type": "total", "total": total_count})

            all_partners = list(data.get("partnerInfo", []))

            for page in range(2, total_pages + 1):
                yield _event({"type": "status", "message": f"Načítám stránku {page}/{total_pages}..."})
                try:
                    r = http_requests.get(
                        f"{DAHUA_CEEN_BASE}?id={country_id}&child=all&page={page}",
                        headers=DAHUA_HEADERS, timeout=15,
                    )
                    r.raise_for_status()
                    all_partners.extend(_parse_dahua_nuxt(r.text).get("partnerInfo", []))
                except Exception as pe:
                    log.error(f"Dahua page {page} failed: {pe}")

            emitted = 0
            for item in all_partners:
                name = (item.get("partner_name") or "").strip()
                if not name:
                    continue

                address = (item.get("partner_text") or item.get("address") or "").strip()
                pseudo_id = f"dahua_{hashlib.md5((name + country_id).encode()).hexdigest()[:12]}"

                existing = db.query(Supplier).filter(Supplier.google_id == pseudo_id).first()
                status = "new"
                if existing:
                    status = existing.status
                    if status in ["rejected", "skipped_forever"]:
                        continue

                email_raw = (item.get("partner_email") or "").strip()
                email = email_raw.split("/")[0].strip() if email_raw else None

                logo = item.get("partner_image") or None

                supplier = {
                    "google_id": pseudo_id,
                    "name": name,
                    "phone": (item.get("partner_tel") or "").strip() or None,
                    "email": email,
                    "website": (item.get("partner_url") or "").strip() or None,
                    "address": address or None,
                    "description": None,
                    "images": [logo] if logo else [],
                    "rating": None,
                    "reviews_count": None,
                    "status": status,
                    "country": country_name,
                    "source": "WEB SEARCH",
                    "tag_source_search": "WEB SEARCH",
                    "tag_keyword": "DAHUA",
                    "tag_location": country_name.upper(),
                    "keyword": "DAHUA",
                }
                yield _event({"type": "supplier", "data": supplier})
                emitted += 1

            yield _event({"type": "done", "total": emitted})

        except Exception as e:
            log.error(f"Dahua stream error: {e}")
            yield _event({"type": "error", "message": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
