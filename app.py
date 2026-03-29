from flask import Flask, send_from_directory, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "sharknet_secret_key"


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="sharknet"
    )
    return conn


# -----------------------------
# AUTO CREATE DATABASE TABLES
# -----------------------------
def init_db():

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        author TEXT
    )
    """)

    conn.commit()
    conn.close()

    print("Database ready")


# run database creation automatically
init_db()


# -----------------------------
# LOGIN PAGE
# -----------------------------
@app.route("/")
def login():
    return send_from_directory("UI", "login.html")


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/home")
@app.route("/home.html")
def home():

    if "user" not in session:
        return redirect("/")

    return send_from_directory("UI", "home.html")


# -----------------------------
# DISCUSSIONS PAGE
# -----------------------------
@app.route("/discussions")
@app.route("/discussions.html")
def discussions():

    if "user" not in session:
        return redirect("/")

    return send_from_directory("UI", "discussions.html")


# -----------------------------
# TUTORS PAGE
# -----------------------------
@app.route("/tutors")
@app.route("/tutors.html")
def tutors():

    if "user" not in session:
        return redirect("/")

    return send_from_directory("UI", "tutors.html")


# -----------------------------
# CSS FILES
# -----------------------------
@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory("css", filename)


# -----------------------------
# IMAGE FILES
# -----------------------------
@app.route("/images/<path:filename>")
def image_files(filename):
    return send_from_directory("images", filename)


# -----------------------------
# LOGIN PROCESS
# -----------------------------
@app.route("/login", methods=["POST"])
def login_process():

    email = request.form["email"]

    if not email.endswith("@mynsu.nova.edu"):
        return "Only NSU student emails allowed"

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM USERS WHERE nsu_email = %s",
        (email,)
    ).fetchone()

    if user is None:

        conn.execute(
            "INSERT INTO USERS (nsu_email) VALUES (%s)",
            (email,)
        )

        conn.commit()

    session["user"] = email

    conn.close()

    print("LOGIN:", email)

    return redirect("/home.html")


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# -----------------------------
# SERVER START
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
