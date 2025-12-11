from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

DB_NAME = "leave_records.db"

# ========= DB HELPER FUNCTIONS =========
def init_db():
    """Create the database and table if it doesn't exist."""
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
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT name, roll_no, date, reason, timestamp FROM records ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()

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
    # templates/student.html
    return render_template("student.html")


@app.route("/admin")
def admin():
    # templates/admin.html
    return render_template("admin.html")


# ========= APIS =========

@app.route("/api/submit_leave", methods=["POST"])
def submit_leave():
    data = request.get_json() or {}

    name = data.get("name")
    roll_no = data.get("roll_no")
    date = data.get("date")
    reason = data.get("reason")

    if not all([name, roll_no, date, reason]):
        return jsonify({"error": "All fields are required"}), 400

    add_record(name, roll_no, date, reason)

    return jsonify({
        "message": "Leave submitted successfully!",
        "new_attendance_percentage": 90,   # dummy value
        "last_leave_date": date
    }), 200


@app.route("/api/records", methods=["GET"])
def get_records_api():
    records = get_all_records()
    return jsonify(records), 200


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

