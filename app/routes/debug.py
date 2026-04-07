from fastapi import APIRouter
import os
from ..logger import log, LOG_FILE

router = APIRouter()

@router.get("/logs")
def get_system_logs(lines: int = 150):
    """Vrátí posledních 'lines' řádků z app.log pro debug účely."""
    if not os.path.exists(LOG_FILE):
        return {"logs": ["Log soubor zatím neexistuje nebo je prázdný."]}
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return {"logs": [line.strip() for line in all_lines[-lines:]]}
    except Exception as e:
        return {"logs": [f"Chyba při čtení logů: {str(e)}"]}
