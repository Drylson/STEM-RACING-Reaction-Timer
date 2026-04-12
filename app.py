import os
import sqlite3
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")  # set by Railway/Render automatically

# ── helpers ──────────────────────────────────────────────────────────────────

def get_conn():
    """Return a DB connection (PostgreSQL in prod, SQLite locally)."""
    if DATABASE_URL:
        import psycopg2
        # Railway uses postgres:// but psycopg2 needs postgresql://
        url = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return psycopg2.connect(url)
    else:
        db_path = os.path.join(os.path.dirname(__file__), "leaderboard.db")
        return sqlite3.connect(db_path)


def ph():
    """Return the right placeholder for the active DB driver."""
    return "%s" if DATABASE_URL else "?"


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id         SERIAL PRIMARY KEY,
            username   TEXT        NOT NULL,
            reaction_ms INTEGER    NOT NULL,
            created_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/submit", methods=["POST"])
def submit_score():
    data = request.get_json()
    username = (data.get("username") or "").strip()[:20]
    reaction_ms = data.get("reaction_ms")

    if not username or not isinstance(reaction_ms, (int, float)) or reaction_ms <= 0:
        return jsonify({"error": "Invalid data"}), 400

    conn = get_conn()
    cur = conn.cursor()
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
    cur = conn.cursor()
    cur.execute("""
        SELECT username, MIN(reaction_ms) AS best_ms
        FROM scores
        GROUP BY LOWER(username)
        ORDER BY best_ms ASC
        LIMIT 15
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"username": r[0], "best_ms": r[1]} for r in rows])


# ── init on startup (works for both gunicorn and direct run) ──────────────────

with app.app_context():
    init_db()

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  🏎️  F1 Reaction Timer arrancando...")
    print("  Abre tu navegador en:  http://localhost:5000\n")
    app.run(debug=False, port=5000)
