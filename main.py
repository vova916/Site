from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from werkzeug.utils import secure_filename

# -------------------- Налаштування --------------------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = '278uhysc7823r7h'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

users = {
    'user1': 'password1',
    'user2': 'password2'
}

MAX_NEWS_ITEMS = 12  # новини
MAX_MEMORY_ITEMS = 8  # спогади

# -------------------- Функції --------------------
def get_db():
    conn = sqlite3.connect("news.db")
    conn.row_factory = sqlite3.Row  
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = get_db()
    # Таблиця новин та спогадів
    conn.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            img TEXT,
            memory INTEGER DEFAULT 0
        )
    ''')
    # Таблиця розкладів
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            img TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# -------------------- Маршрути --------------------
@app.route('/')
def home():
    conn = get_db()
    news_items = conn.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    schedule_items = conn.execute("SELECT * FROM schedules ORDER BY id DESC").fetchall()
    conn.close()
    return render_template('index.html', news=news_items, schedules=schedule_items)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/panel')
def panel():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template('panel_admin.html', user=session["user"])

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and users[username] == password:
            session["user"] = username
            return redirect(url_for("panel"))
        else:
            return render_template("login.html", error="Неправильний логін або пароль")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))

# -------------------- Новини / Спогади --------------------
@app.route('/news', methods=["GET", "POST"])
def news():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        memory = int(request.form.get("memory", 0))  # 0 = новина, 1 = спогад
        file = request.files.get("image")
        img_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            img_path = f"uploads/{filename}"

        conn.execute("INSERT INTO news (title, content, img, memory) VALUES (?, ?, ?, ?)", 
                     (title, content, img_path, memory))
        conn.commit()

        # Видаляємо зайві новини
        conn.execute("""
            DELETE FROM news
            WHERE memory = 0 AND id NOT IN (
                SELECT id FROM news WHERE memory = 0 ORDER BY id DESC LIMIT ?
            )
        """, (MAX_NEWS_ITEMS,))

        # Видаляємо зайві спогади
        conn.execute("""
            DELETE FROM news
            WHERE memory = 1 AND id NOT IN (
                SELECT id FROM news WHERE memory = 1 ORDER BY id DESC LIMIT ?
            )
        """, (MAX_MEMORY_ITEMS,))
        conn.commit()
        conn.close()
        return redirect(url_for("panel"))

    news_items = conn.execute("SELECT * FROM news ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('news.html', user=session["user"], news=news_items)

# -------------------- Розклади --------------------
@app.route('/add_rozclad', methods=["GET", "POST"])
def add_rozclad():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title")
        file = request.files.get("schedule")
        img_path = None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            img_path = f"uploads/{filename}"

        if title and img_path:
            conn = get_db()
            # Видаляємо старий розклад, щоб залишався тільки один
            conn.execute("DELETE FROM schedules")
            conn.execute("INSERT INTO schedules (title, img) VALUES (?, ?)", (title, img_path))
            conn.commit()
            conn.close()
            return redirect(url_for("panel"))

    return render_template("add_rozclad.html")


@app.route('/news/<int:id>')
def news_detail(id):
    conn = get_db()
    news_item = conn.execute("SELECT * FROM news WHERE id = ?", (id,)).fetchone()
    conn.close()
    if news_item is None:
        return "Новина не знайдена", 404
    return render_template('news_detail.html', news=news_item)


# -------------------- Запуск --------------------
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

