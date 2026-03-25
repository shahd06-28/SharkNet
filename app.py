from flask import Flask, send_from_directory, request, redirect, session
import mysql.connector

# Initialize Flask
app = Flask(__name__)
app.secret_key = "sharknet_secret_key"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",              # 🔴 change if needed
        password="password123",   # 🔴 change if needed
        database="sharknet"
    )


# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------
@app.route("/")
def login():
    return send_from_directory("UI", "login.html")


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------
@app.route("/home")
@app.route("/home.html")
def home():
    if "user" not in session:
        return redirect("/")
    return send_from_directory("UI", "home.html")


# --------------------------------------------------
# DISCUSSIONS PAGE
# --------------------------------------------------
@app.route("/discussions")
@app.route("/discussions.html")
def discussions():
    if "user" not in session:
        return redirect("/")
    return send_from_directory("UI", "discussions.html")


# --------------------------------------------------
# TUTORS PAGE
# --------------------------------------------------
@app.route("/tutors")
@app.route("/tutors.html")
def tutors():
    if "user" not in session:
        return redirect("/")
    return send_from_directory("UI", "tutors.html")


# --------------------------------------------------
# STATIC FILES (CSS + IMAGES)
# --------------------------------------------------
@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory("css", filename)


@app.route("/images/<path:filename>")
def image_files(filename):
    return send_from_directory("images", filename)


# --------------------------------------------------
# LOGIN PROCESS (ADAPTS TO DB PARTNER)
# --------------------------------------------------
@app.route("/login", methods=["POST"])
def login_process():

    email = request.form["email"].strip().lower()

    # Restrict to NSU emails
    if not email.endswith("@mynsu.nova.edu"):
        return "Only NSU student emails allowed"

    conn = get_db()
    cursor = conn.cursor()

    # Try different possible column names (adapt to DB partner)
    try:
        cursor.execute(
            "SELECT * FROM users WHERE nsu_email = %s",
            (email,)
        )
    except:
        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

    user = cursor.fetchone()

    # Insert user if not found (also adaptive)
    if user is None:
        try:
            cursor.execute(
                "INSERT INTO users (nsu_email) VALUES (%s)",
                (email,)
            )
        except:
            cursor.execute(
                "INSERT INTO users (email) VALUES (%s)",
                (email,)
            )

        conn.commit()

    # Save login session
    session["user"] = email

    print("LOGIN:", email)

    cursor.close()
    conn.close()

    return redirect("/home.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# --------------------------------------------------
# SERVER START
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)