from flask import Flask, send_from_directory, request, redirect, session, jsonify

app = Flask(__name__)
app.secret_key = "sharknet_secret_key"


# --------------------------------------------------
# TEMP DATA STORAGE
# --------------------------------------------------
discussions_data = []
next_discussion_id = 1
next_reply_id = 1


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
# STATIC FILES
# --------------------------------------------------
@app.route("/css/<path:filename>")
def css_files(filename):
    return send_from_directory("css", filename)


@app.route("/images/<path:filename>")
def image_files(filename):
    return send_from_directory("images", filename)


# --------------------------------------------------
# LOGIN PROCESS
# --------------------------------------------------
@app.route("/login", methods=["POST"])
def login_process():
    email = request.form.get("email", "").strip().lower()

    if not email:
        return "Email is required", 400

    if not email.endswith("@mynsu.nova.edu"):
        return "Only NSU student emails allowed", 400

    session["user"] = email
    return redirect("/home.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# --------------------------------------------------
# GET DISCUSSIONS BY MAJOR
# --------------------------------------------------
@app.route("/api/discussions", methods=["GET"])
def get_discussions():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    major = request.args.get("major")

    if not major:
        return jsonify({"error": "Major is required"}), 400

    filtered = [d for d in discussions_data if d["major"] == major]
    return jsonify(filtered), 200


# --------------------------------------------------
# CREATE DISCUSSION
# --------------------------------------------------
@app.route("/api/discussions", methods=["POST"])
def create_discussion():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    global next_discussion_id

    data = request.get_json()

    if not data or not data.get("major") or not data.get("question"):
        return jsonify({"error": "Missing data"}), 400

    new_discussion = {
        "id": next_discussion_id,
        "major": data["major"],
        "question": data["question"],
        "author_email": session["user"],
        "created_at": "Just now",
        "fins_up": 0,
        "replies": []
    }

    discussions_data.append(new_discussion)
    next_discussion_id += 1

    return jsonify(new_discussion), 201


# --------------------------------------------------
# CREATE REPLY (SUPPORTS NESTED REPLIES)
# --------------------------------------------------
@app.route("/api/replies", methods=["POST"])
def create_reply():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    global next_reply_id

    data = request.get_json()

    if not data or not data.get("discussion_id") or not data.get("reply_text"):
        return jsonify({"error": "Missing data"}), 400

    discussion_id = data["discussion_id"]
    parent_reply_id = data.get("parent_reply_id")

    new_reply = {
        "id": next_reply_id,
        "reply_text": data["reply_text"],
        "author_email": session["user"],
        "created_at": "Just now",
        "children": []
    }

    for discussion in discussions_data:
        if discussion["id"] == discussion_id:
            if parent_reply_id is None:
                discussion["replies"].append(new_reply)
            else:
                def add_to_parent(reply_list):
                    for reply in reply_list:
                        if reply["id"] == parent_reply_id:
                            reply["children"].append(new_reply)
                            return True
                        if add_to_parent(reply["children"]):
                            return True
                    return False

                added = add_to_parent(discussion["replies"])

                if not added:
                    return jsonify({"error": "Parent reply not found"}), 404

            next_reply_id += 1
            return jsonify(new_reply), 201

    return jsonify({"error": "Discussion not found"}), 404


# --------------------------------------------------
# FINS UP
# --------------------------------------------------
@app.route("/api/fins_up", methods=["POST"])
def fins_up():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data or not data.get("discussion_id"):
        return jsonify({"error": "discussion_id required"}), 400

    discussion_id = data["discussion_id"]

    for discussion in discussions_data:
        if discussion["id"] == discussion_id:
            discussion["fins_up"] += 1
            return jsonify({
                "discussion_id": discussion_id,
                "fins_up": discussion["fins_up"]
            })

    return jsonify({"error": "Discussion not found"}), 404


# --------------------------------------------------
# START SERVER
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)