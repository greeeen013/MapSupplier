import logging
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = "app.log"

def setup_logger():
    logger = logging.getLogger("MapSupplier")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # 5MB max size per log file, keeps 2 backups
        handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Also log to console
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        logger.addHandler(console)
        
    return logger

log = setup_logger()
