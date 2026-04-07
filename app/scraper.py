import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def advanced_scrape_emails(base_url: str, timeout: int = 8) -> dict:
    """
    Scrapes the base_url recursively up to depth 2 using BFS.
    Prioritizes links containing contact/about/supplier keywords.
    Returns a dict with 'emails' and 'logs'.
    """
    emails = set()
    visited_urls = set()
    logs = []

    def log_msg(msg):
        logs.append(msg)
        print(msg)
        
    log_msg(f"-> Analýza domény: {base_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    contact_keywords = ["kontakt", "contact", "about", "o-nas", "onas", "spojeni", "supplier", "dodavatel", "impressum", "support", "help"]
    
    if not base_url.startswith("http"):
        base_url = "http://" + base_url
        
    try:
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc
    except Exception as e:
        log_msg(f"-> Chyba parsování URL: {e}")
        return {"emails": [], "logs": logs}

    email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    
    def extract_from_html(html_text):
        found = set()
        soup = BeautifulSoup(html_text, 'html.parser')
        
        for a in soup.select('a[href^="mailto:"]'):
            href = a.get('href')
            if href:
                clean_email = href.replace('mailto:', '').split('?')[0].strip()
                if '@' in clean_email:
                    found.add(clean_email.lower())
                    
        text = soup.get_text(separator=' ')
        for ex in email_regex.findall(text):
            lowered = ex.lower()
            if not lowered.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.js', '.css', '.woff', '.ttf')):
                found.add(lowered)
        return found, soup

    queue = [(base_url, 0)]
    pages_scraped = 0
    MAX_PAGES = 8
    MAX_DEPTH = 2

    while queue and pages_scraped < MAX_PAGES:
        current_url, depth = queue.pop(0)
        
        normalized_url = current_url.rstrip("/")
        if normalized_url in visited_urls:
            continue
            
        visited_urls.add(normalized_url)
        pages_scraped += 1
        
        log_msg(f"-> Úroveň {depth}: Stahování {current_url}")
        
        try:
            resp = requests.get(current_url, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                log_msg(f"   -> Neplatný status kód: {resp.status_code}")
                continue
                
            page_emails, soup = extract_from_html(resp.text)
            if page_emails:
                log_msg(f"   -> Nalezeny emaily: {', '.join(page_emails)}")
                emails.update(page_emails)
            else:
                log_msg(f"   -> Žádné emaily nenalezeny na této stránce.")
                
            if depth < MAX_DEPTH:
                page_links = set()
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urljoin(resp.url, href)
                    try:
                        parsed_link = urlparse(full_url)
                        if parsed_link.netloc == parsed_base.netloc or not parsed_link.netloc:
                            path_and_query = (parsed_link.path + parsed_link.query).lower()
                            if any(kw in path_and_query for kw in contact_keywords):
                                page_links.add(full_url)
                    except Exception:
                        pass
                
                added = 0
                for link in list(page_links)[:5]:  # max 5 relevant links per page
                    norm_link = link.rstrip("/")
                    if norm_link not in visited_urls:
                        queue.append((link, depth + 1))
                        added += 1
                if added > 0:
                    log_msg(f"   -> Přidáno {added} pod-stránek do fronty pro prohledání.")
                        
        except requests.exceptions.Timeout:
            log_msg(f"   -> Vypršel čas (Timeout) na {current_url}")
        except Exception as e:
            log_msg(f"   -> HTTP Chyba: {e}")
            
    log_msg(f"-> Dokončeno. Prohledáno stránek: {pages_scraped}. Celkem nalezeno {len(emails)} emailů.")
    return {"emails": list(emails), "logs": logs}
