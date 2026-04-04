import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE threads ADD COLUMN created_at TEXT")
cursor.execute("ALTER TABLE replies ADD COLUMN created_at TEXT")

conn.commit()
conn.close()

print("Timestamp adicionado!")