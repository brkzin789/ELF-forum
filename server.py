from datetime import datetime
import os
from werkzeug.utils import secure_filename
import sqlite3
from flask import Flask, render_template, request, redirect, make_response
import random
import re

app = Flask(__name__)

# Garantir que a pasta de uploads exista
os.makedirs("static/uploads", exist_ok=True)

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# Muitas boards, estilo 4chan
boards = [
    "dev", "chat", "ideas", "tech", "games", "music", "anime",
    "fun", "random", "movies", "art", "literature", "food", "travel"
]

# Função para transformar >>123 em links clicáveis
def format_text(text):
    return re.sub(r'>>(\d+)', r'<a class="quote" href="/thread/\1">&gt;&gt;\1</a>', text)

# ================== UTIL ==================
def get_anon_cookie():
    anon = request.cookies.get("anon_cookie")
    if not anon:
        anon = str(random.randint(100000, 999999))
    return anon

# ================== ROTA INICIAL ==================
@app.route("/")
def index():
    db = get_db()
    cursor = db.cursor()
    thread_counts = {}
    for b in boards:
        cursor.execute("SELECT COUNT(*) AS cnt FROM threads WHERE board = ?", (b,))
        thread_counts[b] = cursor.fetchone()["cnt"]
    return render_template("index.html", boards=boards, thread_counts=thread_counts)

# ================== BOARD ==================
@app.route("/<board>", methods=["GET", "POST"])
def board_page(board):
    if board not in boards:
        return "Board não existe", 404

    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()

    # ===== CRIAR THREAD =====
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if not content:
            return redirect(f"/{board}")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = format_text(content)

        file = request.files.get("image")
        filename = None
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join("static/uploads", filename))

        cursor.execute(
            "INSERT INTO threads (board, content, anon_cookie, image, timestamp) VALUES (?, ?, ?, ?, ?)",
            (board, content, anon_cookie, filename, timestamp)
        )
        db.commit()
        resp = make_response(redirect(f"/{board}"))
        resp.set_cookie("anon_cookie", anon_cookie)
        return resp

    # ===== FILTRO POR DATA E PESQUISA =====
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    search_query = request.args.get("q", "").strip()

    sql = "SELECT threads.*, (SELECT COUNT(*) FROM replies WHERE replies.thread_id = threads.id) AS reply_count FROM threads WHERE board = ?"
    params = [board]

    if start_date:
        sql += " AND timestamp >= ?"
        params.append(start_date)
    if end_date:
        sql += " AND timestamp <= ?"
        params.append(end_date)
    if search_query:
        sql += " AND content LIKE ?"
        params.append(f"%{search_query}%")

    sql += " ORDER BY timestamp DESC"

    cursor.execute(sql, params)
    threads = cursor.fetchall()

    resp = make_response(render_template("board.html", board=board, threads=threads,
                                         start_date=start_date, end_date=end_date, search_query=search_query,
                                         anon_cookie=anon_cookie))
    resp.set_cookie("anon_cookie", anon_cookie)
    return resp

# ================== THREAD ==================
@app.route("/thread/<int:id>")
def thread_page(id):
    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()

    cursor.execute("SELECT * FROM threads WHERE id = ?", (id,))
    thread = cursor.fetchone()
    if not thread:
        return "Thread não encontrada", 404

    cursor.execute("SELECT * FROM replies WHERE thread_id = ? ORDER BY id ASC", (id,))
    replies = cursor.fetchall()

    formatted_replies = [
        {
            "id": r["id"],
            "anon_cookie": r["anon_cookie"],
            "content": format_text(r["content"]),
            "timestamp": r["timestamp"]
        } for r in replies
    ]

    resp = make_response(render_template(
        "thread.html",
        thread={
            "id": thread["id"],
            "anon_cookie": thread["anon_cookie"],
            "content": format_text(thread["content"]),
            "image": thread["image"],
            "timestamp": thread["timestamp"],
            "board": thread["board"]
        },
        replies=formatted_replies,
        anon_cookie=anon_cookie
    ))
    resp.set_cookie("anon_cookie", anon_cookie)
    return resp

# ================== REPLY ==================
@app.route("/reply/<int:id>", methods=["POST"])
def reply(id):
    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()

    content = request.form.get("content", "").strip()
    if not content:
        return redirect(f"/thread/{id}")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = format_text(content)

    cursor.execute(
        "INSERT INTO replies (thread_id, content, anon_cookie, timestamp) VALUES (?, ?, ?, ?)",
        (id, content, anon_cookie, timestamp)
    )
    db.commit()
    resp = make_response(redirect(f"/thread/{id}"))
    resp.set_cookie("anon_cookie", anon_cookie)
    return resp

# ================== DELETAR THREAD ==================
@app.route("/delete/thread/<int:id>", methods=["POST"])
def delete_thread(id):
    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()

    cursor.execute("SELECT anon_cookie FROM threads WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        return "Thread não encontrada", 404

    if row["anon_cookie"] != anon_cookie:
        return "Você não pode deletar esta thread", 403

    cursor.execute("DELETE FROM threads WHERE id = ?", (id,))
    cursor.execute("DELETE FROM replies WHERE thread_id = ?", (id,))
    db.commit()
    return redirect("/")

# ================== DELETAR REPLY ==================
@app.route("/delete/reply/<int:id>", methods=["POST"])
def delete_reply(id):
    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()

    cursor.execute("SELECT anon_cookie, thread_id FROM replies WHERE id = ?", (id,))
    row = cursor.fetchone()
    if not row:
        return "Reply não encontrada", 404

    if row["anon_cookie"] != anon_cookie:
        return "Você não pode deletar esta reply", 403

    cursor.execute("DELETE FROM replies WHERE id = ?", (id,))
    db.commit()
    return redirect(f"/thread/{row['thread_id']}")

# ================== EXECUTAR ==================

    import os
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
