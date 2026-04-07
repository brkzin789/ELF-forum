from datetime import datetime
import os
import time
from werkzeug.utils import secure_filename
import sqlite3
from flask import Flask, render_template, request, redirect, make_response
import random
import re
import urllib.request
import xml.etree.ElementTree as ET

app = Flask(__name__)

os.makedirs("static/uploads", exist_ok=True)

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

boards = [
    "dev", "chat", "ideas", "tech", "games", "music", "anime",
    "fun", "random", "movies", "art", "literature", "food", "travel"
]

def format_text(text):
    return re.sub(r'>>(\d+)', r'<a class="quote" href="/thread/\1">&gt;&gt;\1</a>', text)

def get_anon_cookie():
    anon = request.cookies.get("anon_cookie")
    if not anon:
        anon = str(random.randint(100000, 999999))
    return anon

def get_news(limit=5, detailed=False):
    try:
        ts = int(time.time())
        url = f"https://feeds.bbci.co.uk/portuguese/rss.xml?t={ts}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        ns = {'media': 'http://search.yahoo.com/mrss/'}
        news_list = []
        items = root.findall('./channel/item')
        random.shuffle(items)
        
        for item in items[:limit]:
            title = item.find('title').text if item.find('title') is not None else "Sem título"
            link = item.find('link').text if item.find('link') is not None else "#"
            
            img_url = None
            media_thumb = item.find('media:thumbnail', ns)
            if media_thumb is not None:
                img_url = media_thumb.get('url')
            else:
                media_content = item.find('media:content', ns)
                if media_content is not None:
                    img_url = media_content.get('url')

            news_dict = {'title': title, 'link': link, 'img': img_url}
            
            if detailed:
                desc_element = item.find('description')
                if desc_element is not None and desc_element.text:
                    clean_desc = re.sub('<[^<]+?>', '', desc_element.text)
                    # Aumentado para permitir expansão de texto no ELF
                    news_dict['desc'] = clean_desc[:500] 
                else:
                    news_dict['desc'] = "Notícia atualizada. Clique para ler os detalhes na fonte."
                
            news_list.append(news_dict)
        return news_list
    except Exception as e:
        print(f"ERRO AO BUSCAR NOTICIAS: {e}")
        return []

def get_sidebar_data():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM threads")
    t_count = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) as total FROM replies")
    r_count = cursor.fetchone()['total']
    
    return {
        "total_posts": t_count + r_count, 
        "news": get_news(limit=5), 
        "online": random.randint(12, 48) 
    }

@app.route("/")
def index():
    data = get_sidebar_data()
    feed_news = get_news(limit=15, detailed=True)
    resp = make_response(render_template("index.html", boards=boards, feed_news=feed_news, **data))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp

# ... (restante das rotas de board, thread, reply permanecem iguais)

@app.route("/<board>", methods=["GET", "POST"])
def board_page(board):
    if board not in boards: return "Board nao existe", 404
    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()
    data = get_sidebar_data()
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file = request.files.get("image")
            filename = None
            if file and file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join("static/uploads", filename))
            cursor.execute("INSERT INTO threads (board, content, anon_cookie, image, timestamp) VALUES (?, ?, ?, ?, ?)",
                           (board, format_text(content), anon_cookie, filename, timestamp))
            db.commit()
        return redirect(f"/{board}")
    search_query = request.args.get("q", "").strip()
    sql = "SELECT threads.*, (SELECT COUNT(*) FROM replies WHERE replies.thread_id = threads.id) AS reply_count FROM threads WHERE board = ?"
    params = [board]
    if search_query: 
        sql += " AND content LIKE ?"
        params.append(f"%{search_query}%")
    sql += " ORDER BY timestamp DESC"
    cursor.execute(sql, params)
    threads = cursor.fetchall()
    resp = make_response(render_template("board.html", board=board, threads=threads, boards=boards, anon_cookie=anon_cookie, **data))
    resp.set_cookie("anon_cookie", anon_cookie)
    return resp

@app.route("/thread/<int:id>")
def thread_page(id):
    db = get_db()
    cursor = db.cursor()
    anon_cookie = get_anon_cookie()
    data = get_sidebar_data()
    cursor.execute("SELECT * FROM threads WHERE id = ?", (id,))
    thread = cursor.fetchone()
    if not thread: return "Thread nao encontrada", 404
    cursor.execute("SELECT * FROM replies WHERE thread_id = ? ORDER BY id ASC", (id,))
    replies = cursor.fetchall()
    resp = make_response(render_template("thread.html", thread=thread, replies=replies, boards=boards, anon_cookie=anon_cookie, **data))
    resp.set_cookie("anon_cookie", anon_cookie)
    return resp

@app.route("/reply/<int:id>", methods=["POST"])
def reply(id):
    db = get_db()
    cursor = db.cursor()
    content = request.form.get("content", "").strip()
    if content:
        cursor.execute("INSERT INTO replies (thread_id, content, anon_cookie, timestamp) VALUES (?, ?, ?, ?)",
                       (id, format_text(content), get_anon_cookie(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        db.commit()
    return redirect(f"/thread/{id}")

@app.route("/delete/thread/<int:id>", methods=["POST"])
def delete_thread(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM threads WHERE id = ? AND anon_cookie = ?", (id, get_anon_cookie()))
    db.commit()
    return redirect("/")

@app.route("/delete/reply/<int:id>", methods=["POST"])
def delete_reply(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT thread_id FROM replies WHERE id = ? AND anon_cookie = ?", (id, get_anon_cookie()))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM replies WHERE id = ?", (id,))
        db.commit()
        return redirect(f"/thread/{row['thread_id']}")
    return "Erro", 403

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))from datetime import datetime
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
