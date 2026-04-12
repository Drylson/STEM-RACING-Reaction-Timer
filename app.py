import os
import sqlite3
import json
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DATABASE_URL   = os.environ.get("DATABASE_URL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin1234")

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn():
    if DATABASE_URL:
        import psycopg2
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    db_path = os.path.join(os.path.dirname(__file__), "leaderboard.db")
    return sqlite3.connect(db_path)

def ph():
    return "%s" if DATABASE_URL else "?"

def init_db():
    conn = get_conn()
    cur  = conn.cursor()
    if DATABASE_URL:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id          SERIAL PRIMARY KEY,
                username    TEXT    NOT NULL,
                reaction_ms INTEGER NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    NOT NULL,
                reaction_ms INTEGER NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
    conn.commit()
    cur.close()
    conn.close()

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    "site_title":   "F1 REACTION TIMER",
    "logo_url":     "",
    "accent_color": "#E8002D",
    "verdicts": json.dumps([
        {"max_ms": 150,   "text": "⚡ INCREÍBLE — Nivel F1",           "color": "#00ff88"},
        {"max_ms": 200,   "text": "🏎️ EXCELENTE — Muy rápido",         "color": "#88ff44"},
        {"max_ms": 250,   "text": "✅ BUENO — Por encima de la media",  "color": "#ccff00"},
        {"max_ms": 300,   "text": "🟡 NORMAL — Tiempo típico",          "color": "#ffcc00"},
        {"max_ms": 400,   "text": "🐢 LENTO — Puedes mejorar",          "color": "#ff8800"},
        {"max_ms": 99999, "text": "💤 MUY LENTO — ¿Te dormiste?",       "color": "#ff3300"},
    ]),
}

def get_config():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT key, value FROM config")
    rows = dict(cur.fetchall())
    cur.close()
    conn.close()
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(rows)
    return cfg

def set_config(key, value):
    conn = get_conn()
    cur  = conn.cursor()
    if DATABASE_URL:
        cur.execute(
            "INSERT INTO config (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (key, value)
        )
    else:
        cur.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value)
        )
    conn.commit()
    cur.close()
    conn.close()

def admin_logged_in():
    return session.get("admin") is True

# ── Public routes ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config")
def api_config():
    cfg = get_config()
    try:
        cfg["verdicts"] = json.loads(cfg["verdicts"])
    except Exception:
        cfg["verdicts"] = json.loads(DEFAULT_CONFIG["verdicts"])
    return jsonify(cfg)

@app.route("/api/submit", methods=["POST"])
def submit_score():
    data        = request.get_json()
    username    = (data.get("username") or "").strip()[:20]
    reaction_ms = data.get("reaction_ms")
    if not username or not isinstance(reaction_ms, (int, float)) or reaction_ms <= 0:
        return jsonify({"error": "Invalid data"}), 400
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(
        f"INSERT INTO scores (username, reaction_ms) VALUES ({ph()}, {ph()})",
        (username, int(reaction_ms)),
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/leaderboard")
def leaderboard():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT MIN(username) AS username, MIN(reaction_ms) AS best_ms
        FROM scores
        GROUP BY LOWER(username)
        ORDER BY best_ms ASC
        LIMIT 15
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"username": r[0], "best_ms": r[1]} for r in rows])

# ── Admin routes ──────────────────────────────────────────────────────────────

@app.route("/admin")
def admin():
    if not admin_logged_in():
        return render_template("admin_login.html")
    return render_template("admin.html")

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if data.get("password") == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "Contraseña incorrecta"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"ok": True})

@app.route("/api/admin/scores")
def admin_scores():
    if not admin_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT id, username, reaction_ms, created_at FROM scores ORDER BY reaction_ms ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([
        {"id": r[0], "username": r[1], "reaction_ms": r[2], "created_at": str(r[3])}
        for r in rows
    ])

@app.route("/api/admin/scores/<int:score_id>", methods=["PUT"])
def admin_update_score(score_id):
    if not admin_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    data        = request.get_json()
    username    = (data.get("username") or "").strip()[:20]
    reaction_ms = data.get("reaction_ms")
    if not username:
        return jsonify({"error": "Nombre vacío"}), 400
    conn = get_conn()
    cur  = conn.cursor()
    if reaction_ms is not None:
        cur.execute(
            f"UPDATE scores SET username={ph()}, reaction_ms={ph()} WHERE id={ph()}",
            (username, int(reaction_ms), score_id)
        )
    else:
        cur.execute(f"UPDATE scores SET username={ph()} WHERE id={ph()}", (username, score_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/scores/<int:score_id>", methods=["DELETE"])
def admin_delete_score(score_id):
    if not admin_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(f"DELETE FROM scores WHERE id={ph()}", (score_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/config", methods=["GET"])
def admin_get_config():
    if not admin_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    return jsonify(get_config())

@app.route("/api/admin/config", methods=["POST"])
def admin_set_config():
    if not admin_logged_in():
        return jsonify({"error": "No autorizado"}), 401
    data = request.get_json()
    for key, value in data.items():
        if key in DEFAULT_CONFIG:
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            set_config(key, str(value))
    return jsonify({"ok": True})

# ── Startup ───────────────────────────────────────────────────────────────────

with app.app_context():
    init_db()

if __name__ == "__main__":
    print("\n  🏎️  F1 Reaction Timer arrancando...")
    print("  Abre tu navegador en:  http://localhost:5000")
    print("  Panel admin en:        http://localhost:5000/admin\n")
    app.run(debug=False, port=5000)

