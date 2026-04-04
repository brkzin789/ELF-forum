import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE threads (
    id INTEGER PRIMARY KEY,
    board TEXT,
    content TEXT,
    anon_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,
    content TEXT,
    anon_id INTEGER
)
""")

conn.commit()
conn.close()

print("Banco criado!")