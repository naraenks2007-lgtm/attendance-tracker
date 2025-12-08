from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Temporary list to store all leave records
records = []

# ====== PAGES ======

# Student portal page
@app.route("/")
def student():
    return render_template("student.html")

# Admin dashboard page
@app.route("/admin")
def admin():
    return render_template("admin.html")

# ====== APIS ======

# Student submits leave
@app.route("/api/submit_leave", methods=["POST"])
def submit_leave():
    data = request.get_json()

    # create a record object
    record = {
        "name": data.get("name"),
        "roll_no": data.get("roll_no"),
        "date": data.get("date"),
        "reason": data.get("reason"),
        "timestamp": datetime.now().isoformat()
    }

    # save into our list (acting like DB)
    records.append(record)

    # send response for student page
    return jsonify({
        "message": "Leave submitted successfully!",
        "new_attendance_percentage": 90,   # dummy value
        "last_leave_date": data.get("date")
    }), 200

# Admin gets all records
@app.route("/api/records", methods=["GET"])
def get_records():
    return jsonify(records), 200


if __name__ == "__main__":
    app.run(debug=True)
