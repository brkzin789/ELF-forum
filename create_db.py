import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Tabela threads
cursor.execute("""
CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board TEXT NOT NULL,
    content TEXT NOT NULL,
    anon_cookie TEXT NOT NULL,
    image TEXT,
    timestamp TEXT
)
""")

# Tabela replies
cursor.execute("""
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    anon_cookie TEXT NOT NULL,
    timestamp TEXT,
    FOREIGN KEY(thread_id) REFERENCES threads(id)
)
""")

conn.commit()
conn.close()
print("Banco criado/atualizado com sucesso!")