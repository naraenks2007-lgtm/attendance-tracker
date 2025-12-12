from flask import Flask, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

app = Flask(__name__)

DB_NAME = "leave_records.db"

# ========= DB HELPER FUNCTIONS =========
def init_db():
    """Create the database and table if it doesn't exist. Also add extra columns if missing."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    # Create base table (new installs will include the extra columns below)
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

    # Check existing columns and add any missing ones
    cur.execute("PRAGMA table_info(records)")
    cols = [r[1] for r in cur.fetchall()]  # second column is name
    # desired additional columns
    extras = {
        "total_classes": "INTEGER",
        "leaves_taken": "INTEGER",
        "attendance": "REAL"
    }
    for col_name, col_type in extras.items():
        if col_name not in cols:
            cur.execute(f"ALTER TABLE records ADD COLUMN {col_name} {col_type}")
    conn.commit()
    conn.close()


def get_all_records():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # select additional fields if present
    cur.execute("""
        SELECT name, roll_no, date, reason, timestamp,
               total_classes, leaves_taken, attendance
        FROM records
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    records = []
    for row in rows:
        records.append({
            "name": row["name"],
            "roll_no": row["roll_no"],
            "date": row["date"],
            "reason": row["reason"],
            "timestamp": row["timestamp"],
            "total_classes": row["total_classes"],
            "leaves_taken": row["leaves_taken"],
            "attendance": row["attendance"]
        })
    return records


def add_record(name, roll_no, date, reason, total_classes=None, leaves_taken=None, attendance=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO records
            (name, roll_no, date, reason, timestamp, total_classes, leaves_taken, attendance)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, roll_no, date, reason, datetime.now().isoformat(), total_classes, leaves_taken, attendance)
    )
    conn.commit()
    conn.close()


# ========= PAGES =========
@app.route("/")
def home():
    return render_template("login.html")

@app.route("/student")
def student():
    return render_template("student.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ========= APIS =========

@app.route("/api/submit_leave", methods=["POST"])
def submit_leave():
    data = request.get_json() or {}

    name = data.get("name")
    roll_no = data.get("roll_no")
    date = data.get("date")
    reason = data.get("reason")
    total_classes = data.get("total_classes")
    leaves_taken = data.get("leaves_taken")

    # Validation
    if not all([name, roll_no, date, reason, total_classes is not None]):
        return jsonify({"error": "All fields are required (including total_classes)."}), 400

    # ---- REAL ATTENDANCE CALCULATION ----
    try:
        total = int(total_classes)
        leaves = int(leaves_taken) if leaves_taken is not None else 0
        present = max(0, total - leaves)
        attendance_percent = round((present / total) * 100, 2)
    except Exception:
        return jsonify({"error": "Invalid number format for total_classes / leaves_taken."}), 400

    # ---- SAVE LEAVE TO DB ----
    add_record(name, roll_no, date, reason, total_classes=total, leaves_taken=leaves, attendance=attendance_percent)

    # ---- FIND LAST LEAVE DATE FROM DB ----
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT date FROM records WHERE roll_no=? ORDER BY id DESC LIMIT 1", (roll_no,))
    last = cur.fetchone()
    conn.close()

    last_leave_date = last[0] if last else date

    return jsonify({
        "message": "Leave submitted successfully!",
        "new_attendance_percentage": attendance_percent,
        "last_leave_date": last_leave_date
    }), 200


@app.route("/api/records", methods=["GET"])
def get_records_api():
    records = get_all_records()
    return jsonify(records), 200

# serve login page
@app.route("/login")
@app.route("/login.html")
def login_page():
    return render_template("login.html")
if __name__ == "__main__":
    init_db()  # run ONLY locally
    app.run(debug=True)
