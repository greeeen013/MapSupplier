"""
Seed test suppliers into the DB for UI/email testing.

Usage:
    python seed_test_suppliers.py           # interactive prompt for test email
    python seed_test_suppliers.py --clean   # delete all test suppliers first, then insert
"""

import sys
import hashlib

sys.path.insert(0, ".")

from app.database import SessionLocal, engine
from app.models import Base, Supplier

Base.metadata.create_all(bind=engine)


def _google_id(name: str, address: str) -> str:
    h = hashlib.md5(f"{name}{address}".encode()).hexdigest()[:10]
    return f"test_{h}"


def build_test_suppliers(test_email: str):
    return [
        {
            "name": "Pneuservis Novák s.r.o.",
            "email": test_email,
            "phone": "+420 731 123 456",
            "address": "Hlavní 12, 602 00 Brno",
            "website": "https://example.com/pneunovak",
            "keyword": "pneu",
            "description": "Prodej a montáž pneumatik všech značek.",
            "rating": 4.5,
            "reviews_count": 82,
            "country": "Czech_Republic",
            "source": "GOOGLE MAPS",
            "tag_source_search": "GOOGLE MAPS",
            "tag_keyword": "PNEU",
            "tag_location": "CZECH_REPUBLIC",
            "status": "accepted",
        },
        {
            "name": "Auto Díly Procházka",
            "email": test_email,
            "phone": "+420 602 987 654",
            "address": "Průmyslová 8, 110 00 Praha",
            "website": "https://example.com/autodily",
            "keyword": "auto díly",
            "description": "Velkoobchod náhradních dílů pro osobní i užitková vozidla.",
            "rating": 4.2,
            "reviews_count": 45,
            "country": "Czech_Republic",
            "source": "AI SEARCH",
            "tag_source_search": "AI SEARCH",
            "tag_keyword": "AUTO DÍLY",
            "tag_location": "CZECH_REPUBLIC",
            "status": "accepted",
        },
        {
            "name": "Gumárna Vysočina a.s.",
            "email": None,
            "phone": "+420 566 001 002",
            "address": "Nádražní 3, 586 01 Jihlava",
            "website": None,
            "keyword": "guma",
            "description": "Výroba technické gumy a gumových profilů.",
            "rating": 3.9,
            "reviews_count": 17,
            "country": "Czech_Republic",
            "source": "GOOGLE MAPS",
            "tag_source_search": "GOOGLE MAPS",
            "tag_keyword": "GUMA",
            "tag_location": "CZECH_REPUBLIC",
            "status": "accepted",
        },
    ]


def clean(db):
    deleted = db.query(Supplier).filter(Supplier.google_id.like("test_%")).delete(synchronize_session=False)
    db.commit()
    print(f"Deleted {deleted} test supplier(s).")


def seed(db, test_email: str):
    suppliers = build_test_suppliers(test_email)
    inserted = 0
    skipped = 0
    for data in suppliers:
        gid = _google_id(data["name"], data.get("address", ""))
        if db.query(Supplier).filter(Supplier.google_id == gid).first():
            skipped += 1
            continue
        db.add(Supplier(google_id=gid, **data))
        inserted += 1
    db.commit()
    print(f"Inserted {inserted} test supplier(s), skipped {skipped} already-existing.")


if __name__ == "__main__":
    test_email = input("Zadej testovací email (emaily dodavatelů budou nastaveny na tuto adresu): ").strip()
    if not test_email:
        print("Email nesmí být prázdný.")
        sys.exit(1)

    db = SessionLocal()
    try:
        if "--clean" in sys.argv:
            clean(db)
        seed(db, test_email)
    finally:
        db.close()
