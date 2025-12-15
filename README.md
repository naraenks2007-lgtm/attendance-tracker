# 📘 Attendance Tracker

A simple **Student–Admin Attendance Management System** built using **Flask (Python)** and **MongoDB**, with a clean frontend for students and a protected admin dashboard. This project is designed for learning full‑stack concepts and is deployable on **Render**.

---

## 🚀 Features

### 👨‍🎓 Student Module

* Secure student login
* Username format validation: `25am0XX` (XX = 01 to 62)
* Submit daily attendance
* Enter number of sessions absent (out of 6)
* Automatic attendance percentage calculation
* Leave reason and leave date
* View:

  * Total sessions
  * Attendance percentage
  * Last leave date
  * Total leave count

### 👨‍🏫 Admin Module

* Admin login via `/admin` route (not visible publicly)
* View all student attendance records
* Persistent data storage using MongoDB
* Protected routes using Flask sessions

---

## 🛠️ Tech Stack

### Frontend

* HTML5
* CSS3 (Responsive Design)
* JavaScript
* Lottie.js (animations)

### Backend

* Python (Flask)
* MongoDB (Atlas)
* PyMongo

### Deployment

* Render (Web Service)

---

## 📁 Project Structure

```
attendance-tracker/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   ├── login.html
│   ├── student.html
│   └── admin.html
│
├── static/
│   ├── styles.css
│   └── styles.responsive.css
│
└── .gitignore
```

---

## ⚙️ Installation & Setup (Local)

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/attendance-tracker.git
cd attendance-tracker
```

### 2️⃣ Create Virtual Environment (Optional but Recommended)

```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Setup MongoDB

* Create a **MongoDB Atlas** account
* Create a cluster
* Get the **MongoDB URI**

Set it as an environment variable:

```bash
MONGO_URI=your_mongodb_connection_string
```

### 5️⃣ Run the App

```bash
python app.py
```

Open browser:

```
http://127.0.0.1:5000
```

---

## 🌍 Deployment on Render

1. Push your code to GitHub
2. Create a **New Web Service** in Render
3. Connect your GitHub repository
4. Set:

   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app`
5. Add Environment Variable:

   * `MONGO_URI = your_mongodb_uri`
6. Deploy 🎉

---

## 🔐 Admin Access

* Admin dashboard URL:

```
/admin
```

* Admin credentials are defined securely in backend code

---

## 📌 Notes

* SQLite is **not recommended** on Render (data resets)
* MongoDB ensures **persistent storage**
* Designed for learning backend, databases, and deployment

---

## 📷 Screenshots (Optional)

*Add screenshots of login page, student dashboard, and admin panel here.*

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Open a Pull Request

---

## 📜 License

This project is for **educational purposes**.

---

## 🙌 Acknowledgements

Built with ❤️ for learning **Flask, MongoDB, and Full‑Stack Development**.

---

### ✨ Author

**Naraen K S**

Happy Coding 🚀
