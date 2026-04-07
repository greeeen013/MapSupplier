import sqlite3

try:
    conn = sqlite3.connect('c:\\programovani\\do prace\\MapSupplier\\suppliers.db')
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE suppliers ADD COLUMN country VARCHAR;")
    print("Column 'country' added successfully.")
    conn.commit()
except sqlite3.OperationalError as e:
    print(f"OperationalError: {e}")
finally:
    conn.close()
