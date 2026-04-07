import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Tabela Threads com as colunas que o seu server.py pede
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS threads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        board TEXT NOT NULL,
        content TEXT NOT NULL,
        anon_cookie TEXT NOT NULL,
        image TEXT,
        timestamp TEXT NOT NULL
    )""")
    
    # Tabela Replies
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        thread_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        anon_cookie TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (thread_id) REFERENCES threads (id)
    )""")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
