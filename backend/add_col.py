import sqlite3
conn = sqlite3.connect("yukti.db")
try:
    conn.execute("ALTER TABLE sessions ADD COLUMN financial_overrides JSON DEFAULT '{}'")
    print("Column added")
except Exception as e:
    print(e)
conn.commit()
