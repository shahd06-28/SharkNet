from flask import Flask, send_from_directory, request, redirect, session, jsonify
import sqlite3

# Initialize Flask
app = Flask(__name__)

# Secret key for session management
app.secret_key = "sharknet_secret_key"


# -----------------------------
# DATABASE CONNECTION
# -----------------------------
def get_db():

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row

    return conn


# -----------------------------
# LOGIN PAGE
# -----------------------------
@app.route("/")
def login():

    return send_from_directory("UI", "login.html")


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/home.html")
def home():

    # Protect page if user not logged in
    if "user" not in session:
        return redirect("/")

    return send_from_directory("UI", "home.html")


# -----------------------------
# DISCUSSIONS PAGE
# -----------------------------
@app.route("/discussions.html")
def discussions():

    if "user" not in session:
        return redirect("/")

    return send_from_directory("UI", "discussions.html")


# -----------------------------
# TUTORS PAGE
# -----------------------------
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

    # Only allow NSU emails
    if not email.endswith("@mynsu.nova.edu"):
        return "Only NSU student emails allowed"

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    ).fetchone()

    # Create user if first login
    if user is None:

        conn.execute(
            "INSERT INTO users (email) VALUES (?)",
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
# CREATE POST (BACKEND API)
# -----------------------------
@app.route("/create_post", methods=["POST"])
def create_post():

    if "user" not in session:
        return redirect("/")

    title = request.form.get("title")
    content = request.form.get("content")

    conn = get_db()

    conn.execute(
        "INSERT INTO posts (title, content, author) VALUES (?, ?, ?)",
        (title, content, session["user"])
    )

    conn.commit()
    conn.close()

    print("POST CREATED:", title)

    return redirect("/discussions.html")


# -----------------------------
# GET POSTS API
# -----------------------------
@app.route("/api/posts")
def get_posts():

    conn = get_db()

    posts = conn.execute(
        "SELECT * FROM posts ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(p) for p in posts])


# -----------------------------
# DELETE POST (CRUD)
# -----------------------------
@app.route("/delete_post/<int:post_id>")
def delete_post(post_id):

    if "user" not in session:
        return redirect("/")

    conn = get_db()

    conn.execute(
        "DELETE FROM posts WHERE id=?",
        (post_id,)
    )

    conn.commit()
    conn.close()

    print("POST DELETED:", post_id)

    return redirect("/discussions.html")


# -----------------------------
# SERVER START
# -----------------------------
if __name__ == "__main__":

   app.run(host="0.0.0.0", port=5000, debug=True)