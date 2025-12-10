from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

DB_NAME = "leave_records.db"


# ========= DB HELPER FUNCTIONS =========
def init_db():
    """Create the database and table if not exists."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            roll_no TEXT,
            date TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_all_records():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # so we can access by column name
    cur = conn.cursor()
    cur.execute("SELECT name, roll_no, date, reason, timestamp FROM records ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

    # convert rows to list of dicts
    records = []
    for row in rows:
        records.append({
            "name": row["name"],
            "roll_no": row["roll_no"],
            "date": row["date"],
            "reason": row["reason"],
            "timestamp": row["timestamp"]
        })
    return records


def add_record(name, roll_no, date, reason):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO records (name, roll_no, date, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        (name, roll_no, date, reason, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


# ========= PAGES =========

@app.route("/")
def student():
    return render_template("student.html")  # :contentReference[oaicite:1]{index=1}


@app.route("/admin")
def admin():
    return render_template("admin.html")    # :contentReference[oaicite:2]{index=2}


# ========= APIS =========

@app.route("/api/submit_leave", methods=["POST"])
def submit_leave():
    data = request.get_json()

    name = data.get("name")
    roll_no = data.get("roll_no")
    date = data.get("date")
    reason = data.get("reason")

    # Save into database instead of list
    add_record(name, roll_no, date, reason)

    return jsonify({
        "message": "Leave submitted successfully!",
        "new_attendance_percentage": 90,   # dummy value
        "last_leave_date": date
    }), 200


@app.route("/api/records", methods=["GET"])
def get_records():
    records = get_all_records()
    return jsonify(records), 200


if __name__ == "__main__":
    # Initialize DB when app starts
    init_db()
    app.run(debug=True)
