# MapSupplier

Web aplikace pro vyhledávání, správu a kontaktování dodavatelů. Kombinuje Google Maps API, Gemini AI a Gmail SMTP.

---

## Spuštění

**Windows:** Dvakrát klikni na `run.bat` — vytvoří venv, nainstaluje závislosti, spustí server.

**Manuálně:**
```bash
venv\Scripts\activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- App: `http://localhost:8000`
- Dev konzole: `http://localhost:8000/test.html`

---

## Konfigurace (.env)

```
GOOGLE_MAPS_API_KEY=...   # Google Places API
GEMINI_API_KEY=...        # Google AI Studio
EMAIL_USER=...            # Gmail adresa
EMAIL_PASSWORD=...        # Gmail App Password (16 znaků, bez mezer)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
```

---

## Databáze

SQLite soubor: `suppliers.db`

SQLAlchemy vytváří tabulky automaticky při spuštění. Pro přidání nových sloupců do existující DB:

```bash
python migrate.py
```

`migrate.py` je idempotentní — opakované spuštění bezpečně přeskočí již existující sloupce.

---

### Tabulka `suppliers`

Hlavní tabulka dodavatelů.

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | INTEGER PK | Auto-increment primární klíč |
| `google_id` | VARCHAR UNIQUE | Google Place ID, nebo `ai_hash_{hash}` pro AI dodavatele |
| `name` | VARCHAR | Název firmy |
| `rating` | FLOAT | Google hodnocení (nullable) |
| `keyword` | VARCHAR | Hledaný výraz při vyhledávání |
| `phone` | VARCHAR | Telefon (nullable) |
| `email` | VARCHAR | Primární e-mail — flat string (nullable) |
| `address` | VARCHAR | Celá adresa |
| `website` | VARCHAR | URL webu (nullable) |
| `images` | JSON | Seznam URL obrázků |
| `reviews_count` | INTEGER | Počet Google recenzí (nullable) |
| `description` | TEXT | Volný popis (nullable) |
| `rejection_reason` | TEXT | Důvod odmítnutí (nullable) |
| `country` | VARCHAR | Země/oblast zadaná při vyhledávání (např. `"Czech_Republic"`) |
| `source` | VARCHAR | Jak byl nalezen: `"AI SEARCH"` nebo `"GOOGLE MAPS"` |
| `status` | VARCHAR | `pending` / `accepted` / `rejected` / `contacted` / `skipped_forever` |
| `created_at` | DATETIME | UTC timestamp, automaticky při insertu |

#### Tagy — tři oddělené sloupce

Místo jednoho JSON pole `tags` jsou tagy uloženy zvlášť pro snadné dotazování:

| Sloupec | Typ | Příklad hodnoty |
|---|---|---|
| `tag_source_search` | VARCHAR | `"AI SEARCH"` nebo `"GOOGLE MAPS"` |
| `tag_keyword` | VARCHAR | `"PNEU"` — klíčové slovo vyhledávání (uppercase) |
| `tag_location` | VARCHAR | `"CZECH_REPUBLIC"` — oblast vyhledávání (uppercase) |

> Sloupec `tags` (JSON) zůstává v tabulce pro zpětnou kompatibilitu se staršími záznamy, ale nová data ho již nevyužívají.

**Příklady dotazů na tagy:**
```sql
-- Všichni dodavatelé z AI vyhledávání
SELECT * FROM suppliers WHERE tag_source_search = 'AI SEARCH';

-- Dodavatelé pro klíčové slovo PNEU
SELECT * FROM suppliers WHERE tag_keyword = 'PNEU';

-- Dodavatelé z Polska
SELECT * FROM suppliers WHERE tag_location = 'POLAND';

-- Kombinace
SELECT * FROM suppliers
WHERE tag_source_search = 'AI SEARCH'
  AND tag_location = 'CZECH_REPUBLIC'
  AND status = 'accepted';
```

---

### Tabulka `email_presets`

Šablony a AI prompty pro hromadné emaily. Používá se i pro uložení vlastních filtrů (`custom_filter`).

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | INTEGER PK | Auto-increment primární klíč |
| `name` | VARCHAR UNIQUE | Název presetu |
| `subject` | VARCHAR | Předmět emailu |
| `body` | TEXT | Tělo emailu (plain text nebo AI prompt) |
| `preset_type` | VARCHAR | `"template"`, `"ai_prompt"`, nebo `"custom_filter"` |

---

## Architektura

Jedna FastAPI aplikace (`app/main.py`) — servíruje REST API i statický frontend z `app/static/`.

### Backend moduly

| Soubor | Účel |
|---|---|
| `app/models.py` | SQLAlchemy ORM: tabulky `Supplier` a `EmailPreset` |
| `app/schemas.py` | Pydantic modely pro request/response validaci |
| `app/database.py` | SQLite engine + `get_db` dependency |
| `app/logger.py` | Rotující file logger (`app.log`, 5 MB × 2 zálohy) |
| `app/gemini_client.py` | Gemini wrapper: fallback chain `gemini-2.5-pro` → `gemini-2.0-flash` → `gemini-1.5-pro` |
| `app/scraper.py` | BFS email crawler — prochází až 8 stránek do hloubky 2 |

### API routery (`app/routes/`)

| Router | Prefix | Účel |
|---|---|---|
| `search.py` | `/api/search` | Google Maps textové vyhledávání + Gemini AI vyhledávání dodavatelů |
| `suppliers.py` | `/api/suppliers` | CRUD dodavatelů; při schválení obohacuje data z Google Place Details |
| `email.py` | `/api/email` | CRUD email presetů, generování emailu přes Gemini, odeslání přes Gmail SMTP |
| `scraper.py` | `/api/scraper` | Testovací endpoint pro `advanced_scrape_emails` |
| `debug.py` | `/api/debug` | Vrací posledních N řádků `app.log` |

### Frontend (`app/static/`)

- `index.html` + `js/main.js` — hlavní SPA: tři vyhledávací pohledy (Google Maps, AI, Web) a pohled Emailing
- `test.html` + `js/test.js` — vývojářská konzole: Gemini profiler, scraper tester, živý log

---

## Tok dat — AI vyhledávání

```
1. Frontend zavolá GET /api/search/ai_places?query=...&location=...
2. Gemini vygeneruje JSON seznam firem (name, address, email)
3. Pro každou firmu:
   a. Google Maps Text Search → reálný google_id, adresa, rating
   b. Google Place Details → website, phone
   c. BFS scraper → ověřené emaily z webu
   d. Pseudo-ID pokud Google nenajde: ai_hash_{hash(jméno+adresa)}
4. Výsledky jdou do frontendu — NEJSOU ještě v DB
5. Uživatel klikne "Potvrdit" → POST /api/suppliers/
6. Při uložení s status=accepted proběhne enrich_data():
   - Google Place Details (phone, website, address)
   - Jednoduchý email scraper pokud email chybí
7. Záznam se uloží do DB s tag_source_search=AI SEARCH
```

## Tok dat — Google Maps vyhledávání

```
1. Frontend zavolá GET /api/search/places?query=...&location=...
2. Google Maps Text Search → seznam míst
3. Výsledky jdou do frontendu — NEJSOU ještě v DB
4. Uživatel klikne "Potvrdit" → POST /api/suppliers/
5. enrich_data() doplní telefon, web, email
6. Záznam se uloží s tag_source_search=GOOGLE MAPS
```

---

## Produkce

SSH přístup:
```bash
ssh abcom@100.78.97.96
cd MapSupplier
```
