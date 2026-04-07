import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "suppliers.db")

MIGRATIONS = [
    ("country", "ALTER TABLE suppliers ADD COLUMN country VARCHAR;"),
    ("source",  "ALTER TABLE suppliers ADD COLUMN source VARCHAR;"),
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for column, sql in MIGRATIONS:
    try:
        cursor.execute(sql)
        print(f"Column '{column}' added successfully.")
    except sqlite3.OperationalError as e:
        print(f"Skipped '{column}': {e}")

conn.commit()
conn.close()
print("Migration complete.")
