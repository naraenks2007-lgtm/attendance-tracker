from flask import Flask, render_template, request, redirect, session, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import date
import re, io

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_RIGHT
import os
app = Flask(__name__)
app.secret_key = "dev-secret"

# ---------------- DB ----------------
MONGO_URI = os.environ.get("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["attendance_db"]


STUDENT_REGEX = r'^25am\d{3}$'
TOTAL_SESSIONS = 6

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        if u == "admin" and p == "admin123":
            session["user"] = "admin"
            session["role"] = "admin"
            return redirect("/admin")

        if re.match(STUDENT_REGEX, u) and p == "12345":
            session["user"] = u
            session["role"] = "student"
            if not users.find_one({"username": u}):
                users.insert_one({"username": u, "name": u})
            return redirect("/student")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- STUDENT ----------------
@app.route("/student", methods=["GET", "POST"])
def student():
    if session.get("role") != "student":
        return redirect("/")

    today = date.today().strftime("%Y-%m-%d")

    # ---------- APPLY LEAVE ----------
    if request.method == "POST":
        leave_date = request.form["date"]

        # ❗ PREVENT DUPLICATE ACTIVE LEAVE
        existing = records.find_one({
            "username": session["user"],
            "date": leave_date,
            "status": {"$in": ["Pending", "Approved"]}
        })
        if not existing:
            records.insert_one({
                "username": session["user"],
                "roll": session["user"],
                "name": request.form["student_name"],
                "date": leave_date,
                "absent_sessions": int(request.form["absent_sessions"]),
                "reason": request.form["reason"],
                "status": "Pending"
            })
        return redirect("/student")

    # ---------- FETCH HISTORY ----------
    history = list(records.find(
        {"username": session["user"]}
    ).sort("_id", -1))

    latest = history[0] if history else None
    approval_status = latest["status"] if latest else "Not Submitted"
    last_leave = latest["date"] if latest else "-"

    # ---------- ABSENT TODAY (ONLY APPROVED) ----------
    approved_today = records.find_one({
        "username": session["user"],
        "date": today,
        "status": "Approved"
    })
    absent_today = approved_today["absent_sessions"] if approved_today else 0

    # ---------- ATTENDANCE ----------
    approved = list(records.find({
        "username": session["user"],
        "status": "Approved"
    }))

    if approved:
        total = len(approved) * TOTAL_SESSIONS
        absent = sum(r["absent_sessions"] for r in approved)
        attendance = round(((total - absent) / total) * 100, 2)
    else:
        attendance = 100

    user = users.find_one({"username": session["user"]})

    return render_template(
        "student.html",
        name=user["name"],
        roll_no=session["user"],
        attendance=attendance,
        absent_today=absent_today,
        last_leave=last_leave,
        approval_status=approval_status,
        history=history
    )

# ---------------- CANCEL LEAVE ----------------
@app.route("/cancel_leave", methods=["POST"])
def cancel_leave():
    records.update_one(
        {"username": session["user"], "status": "Pending"},
        {"$set": {"status": "Cancelled"}}
    )
    return redirect("/student")

# ---------------- ADMIN ----------------
from datetime import date

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/")

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
    if session.get("role") != "admin":
        return redirect("/")

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

@app.route("/admin/pdf")
def admin_pdf():
    if session.get("role") != "admin":
        return redirect("/")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    story = [Paragraph("<b>Attendance Report</b>", styles["Title"])]

    table_data = [["Roll", "Name", "Date", "Absent", "Status"]]

    for r in records.find():
        table_data.append([
            r.get("roll", ""),
            r.get("name", ""),
            r.get("date", ""),
            r.get("absent_sessions", ""),
            r.get("status", "")
        ])

    table = Table(table_data)
    story.append(table)

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Admin_Attendance_Report.pdf",
        mimetype="application/pdf"
    )

# ---------------- STUDENT PDF ----------------
@app.route("/student/leave_pdf")
def leave_pdf():
    if session.get("role") != "student":
        return redirect("/")

    record = records.find_one(
        {"username": session["user"], "status": "Approved"},
        sort=[("_id", -1)]
    )
    if not record:
        return redirect("/student")

    today = date.today().strftime("%d-%m-%Y")
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>LEAVE PERMISSION LETTER</b>", styles["Title"]))
    story.append(Spacer(1, 20))

    right = styles["Normal"]
    right.alignment = TA_RIGHT
    story.append(Paragraph(f"Date: {today}", right))
    story.append(Spacer(1, 20))

    body = f"""
    This is to certify that <b>{record['name']}</b>,
    bearing Roll Number <b>{record['roll']}</b>,
    is permitted to avail leave on <b>{record['date']}</b>
    for <b>{record['absent_sessions']}</b> session(s).

    <br/><br/>
    Leave Status: <b>{record['status']}</b>

    <br/><br/>
    Reason:<br/>{record['reason']}
    """
    story.append(Paragraph(body, styles["Normal"]))
    story.append(Spacer(1, 60))

    # ✅ FIXED PATH (INSIDE FUNCTION)
    signature_path = os.path.join(
        app.root_path, "static", "images", "tutor_signature.png"
    )

    tutor_sign = Image(signature_path, 5 * cm, 2 * cm)

    table = Table(
        [
            ["__________________", tutor_sign],
            [record["name"], "Class Tutor"]
        ],
        colWidths=[7 * cm, 7 * cm]
    )

    story.append(table)
    doc.build(story)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="Leave_Permission_Letter.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    app.run(debug=True)
