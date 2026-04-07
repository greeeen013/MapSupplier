from fastapi import APIRouter
from ..scraper import advanced_scrape_emails

router = APIRouter()

@router.get("/test")
def test_scraper(url: str):
    """
    Test endpoint pro deep email crawler.
    Navrátí nalezené emaily a krok-za-krokem logy.
    """
    result = advanced_scrape_emails(url, timeout=10)
    return result
