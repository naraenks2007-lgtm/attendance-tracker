from flask import (
    Flask, render_template, request,
    redirect, session, jsonify, send_file
)
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os, re, io

# ===================== APP =====================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

# ===================== MONGODB =====================
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise Exception("MONGO_URI environment variable not set")

client = MongoClient(MONGO_URI)
db = client["attendance_db"]

users = db["users"]
records = db["records"]

# ===================== CONSTANTS =====================
STUDENT_REGEX = r'^25am(0[0-5][0-9]|06[0-2])$'
TOTAL_SESSIONS_PER_DAY = 6

# ===================== CREATE ADMIN (ONCE) =====================
if users.count_documents({"role": "admin"}) == 0:
    users.insert_one({
        "username": "admin",
        "password": generate_password_hash("admin123"),
        "role": "admin"
    })

# ===================== AUTH =====================
@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users.find_one({"username": username})

        # ----- ADMIN / EXISTING USER -----
        if user and check_password_hash(user["password"], password):
            session["user"] = username
            session["role"] = user["role"]
            return redirect("/admin" if user["role"] == "admin" else "/student")

        # ----- STUDENT AUTO REGISTER -----
        if re.match(STUDENT_REGEX, username) and password == "12345":
            if not user:
                users.insert_one({
                    "username": username,
                    "password": generate_password_hash("12345"),
                    "role": "student",
                    "name": "Student"
                })
            session["user"] = username
            session["role"] = "student"
            return redirect("/student")

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ===================== STUDENT =====================
@app.route("/student", methods=["GET", "POST"])
def student():
    if "user" not in session or session["role"] != "student":
        return redirect("/login")

    today = date.today().strftime("%Y-%m-%d")

    # ---------- SUBMIT LEAVE ----------
    if request.method == "POST":
        name = request.form["student_name"]
        absent = int(request.form["absent_sessions"])
        reason = request.form["reason"]
        leave_date = request.form["date"]

        # validation
        if absent < 0 or absent > TOTAL_SESSIONS_PER_DAY:
            return redirect("/student")

        # prevent duplicate leave for same date
        if records.find_one({"username": session["user"], "date": leave_date}):
            return redirect("/student")

        users.update_one(
            {"username": session["user"]},
            {"$set": {"name": name}}
        )

        records.insert_one({
            "username": session["user"],
            "name": name,
            "roll": session["user"],
            "date": leave_date,
            "absent_sessions": absent,
            "reason": reason,
            "status": "Pending"
        })

        return redirect("/student")

    # ---------- ATTENDANCE CALC ----------
    approved = list(records.find({
        "username": session["user"],
        "status": "Approved"
    }))

    total_possible = len(approved) * TOTAL_SESSIONS_PER_DAY
    total_absent = sum(r["absent_sessions"] for r in approved)

    attendance = round(
        ((total_possible - total_absent) / total_possible) * 100, 2
    ) if total_possible > 0 else 100

    latest = records.find_one(
        {"username": session["user"]},
        sort=[("_id", -1)]
    )

    approval_status = latest["status"] if latest else "Not Submitted"
    absent_today = (
        latest["absent_sessions"]
        if latest and latest["date"] == today
        else 0
    )
    last_date = latest["date"] if latest else "None"

    history = list(
        records.find({"username": session["user"]}).sort("_id", -1)
    )

    user = users.find_one({"username": session["user"]})

    return render_template(
        "student.html",
        name=user.get("name", "Student"),
        roll_no=session["user"],
        attendance=attendance,
        absent_today=absent_today,
        last_leave=last_date,
        approval_status=approval_status,
        history=history
    )

# ===================== ADMIN =====================
@app.route("/admin")
def admin():
    if "user" not in session or session["role"] != "admin":
        return redirect("/login")

    today = date.today().strftime("%Y-%m-%d")

    leaves = list(records.find().sort("_id", -1))

    today_absent = records.count_documents({
        "date": today,
        "status": "Approved"
    })

    return render_template(
        "admin.html",
        leaves=leaves,
        today_absent=today_absent
    )

@app.route("/admin/action/<id>/<action>")
def admin_action(id, action):
    if "user" not in session or session["role"] != "admin":
        return redirect("/login")

    if action == "approve":
        records.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "Approved"}}
        )
    elif action == "reject":
        records.update_one(
            {"_id": ObjectId(id)},
            {"$set": {"status": "Rejected"}}
        )
    elif action == "delete":
        records.delete_one({"_id": ObjectId(id)})

    return redirect("/admin")

# ===================== ADMIN STATS =====================
@app.route("/admin/stats")
def admin_stats():
    filter_type = request.args.get("type", "week")
    today = datetime.today()

    if filter_type == "today":
        match = {"date": today.strftime("%Y-%m-%d"), "status": "Approved"}
    else:
        days = 30 if filter_type == "month" else 7
        start_date = today - timedelta(days=days)
        match = {
            "status": "Approved",
            "date": {"$gte": start_date.strftime("%Y-%m-%d")}
        }

    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$date", "absent": {"$sum": "$absent_sessions"}}},
        {"$sort": {"_id": 1}}
    ]

    data = list(records.aggregate(pipeline))

    return jsonify({
        "labels": [d["_id"] for d in data],
        "data": [d["absent"] for d in data]
    })

# ===================== ADMIN PDF =====================
@app.route("/admin/pdf")
def admin_pdf():
    if "user" not in session or session["role"] != "admin":
        return redirect("/login")

    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    data = [["Roll", "Name", "Date", "Absent", "Status"]]
    for r in records.find():
        data.append([
            r.get("roll", ""),
            r.get("name", ""),
            r.get("date", ""),
            r.get("absent_sessions", ""),
            r.get("status", "")
        ])

    table = Table(data)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 1, colors.black)
    ]))

    doc.build([table])
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="attendance_report.pdf",
        mimetype="application/pdf"
    )
@app.route("/healthz")
def healthz():
    return "OK", 200

# ===================== RUN =====================
if __name__ == "__main__":
    app.run()
