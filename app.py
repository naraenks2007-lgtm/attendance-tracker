from flask import (
    Flask, render_template, request,
    redirect, session, jsonify, send_file
)
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import date
import os, re, io

# ===================== APP =====================
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ===================== MONGODB =====================
MONGO_URI = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://naraenks2007_db_user:naraen2007@cluster0.fx8z7bx.mongodb.net/attendance_db"
)

client = MongoClient(MONGO_URI)
db = client["attendance_db"]

users = db["users"]
records = db["records"]

# ===================== CONSTANTS =====================
STUDENT_REGEX = r'^25am(0[0-5][0-9]|06[0-2])$'
TOTAL_SESSIONS_PER_DAY = 6

# ===================== CREATE ADMIN =====================
if not users.find_one({"username": "admin"}):
    users.insert_one({
        "username": "admin",
        "password": "admin123",
        "role": "admin",
        "name": "Administrator"
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

        # Admin or existing user
        user = users.find_one({"username": username, "password": password})
        if user:
            session["user"] = username
            session["role"] = user["role"]
            return redirect("/admin" if user["role"] == "admin" else "/student")

        # Student auto-register
        if re.match(STUDENT_REGEX, username) and password == "12345":
            if not users.find_one({"username": username}):
                users.insert_one({
                    "username": username,
                    "password": "12345",
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

    # ---------- ATTENDANCE CALC (APPROVED ONLY) ----------
    approved = list(records.find({
        "username": session["user"],
        "status": "Approved"
    }))

    total_sessions = len(approved) * TOTAL_SESSIONS_PER_DAY
    total_absent = sum(r["absent_sessions"] for r in approved)

    attendance = round(
        ((total_sessions - total_absent) / total_sessions) * 100, 2
    ) if total_sessions > 0 else 100

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

# ===================== ADMIN GRAPH =====================
from datetime import datetime, timedelta

@app.route("/admin/stats")
def admin_stats():
    filter_type = request.args.get("type", "week")
    today = datetime.today()

    if filter_type == "today":
        start = today.strftime("%Y-%m-%d")
        match = {"date": start, "status": "Approved"}

    elif filter_type == "month":
        start_date = today - timedelta(days=30)
        match = {
            "status": "Approved",
            "date": {"$gte": start_date.strftime("%Y-%m-%d")}
        }

    else:  # week (default)
        start_date = today - timedelta(days=7)
        match = {
            "status": "Approved",
            "date": {"$gte": start_date.strftime("%Y-%m-%d")}
        }

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$date",
            "absent": {"$sum": "$absent_sessions"}
        }},
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
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))

    doc.build([table])
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="attendance_report.pdf",
        mimetype="application/pdf"
    )

# ===================== RUN =====================
if __name__ == "__main__":
    app.run()
