from flask import Flask, send_from_directory, request, redirect, session, jsonify, Response
import os
import json
import re

app = Flask(__name__)
app.secret_key = "sharknet_secret_key"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UI_DIR = os.path.join(BASE_DIR, "UI")
DATA_FILE = os.path.join(BASE_DIR, "discussion_data.json")

# --------------------------------------------------
# DATA STORAGE
# --------------------------------------------------
discussions_data = []
next_discussion_id = 1
next_reply_id = 1


def save_data():
    data = {
        "discussions_data": discussions_data,
        "next_discussion_id": next_discussion_id,
        "next_reply_id": next_reply_id
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def load_data():
    global discussions_data, next_discussion_id, next_reply_id

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            discussions_data = data.get("discussions_data", [])
            next_discussion_id = data.get("next_discussion_id", 1)
            next_reply_id = data.get("next_reply_id", 1)
    else:
        discussions_data = []
        next_discussion_id = 1
        next_reply_id = 1


# --------------------------------------------------
# RUNTIME SCRIPT INJECTION FOR ORIGINAL discussions.html
# --------------------------------------------------
DISCUSSIONS_RUNTIME_SCRIPT = r"""
<script>
const params = new URLSearchParams(window.location.search);
const major = params.get("major");

// keeps cards open after re-render
const openDiscussionIds = new Set();

if (major) {
    const main = document.querySelector('main');
    document.getElementById("majors-section").style.display = "none";

    // Title and back button
    const pageTitle = document.createElement("h2");
    pageTitle.textContent = major + " Discussions";
    pageTitle.className = "section-title";

    const backBtn = document.createElement("button");
    backBtn.textContent = "← Back";
    backBtn.className = "back-btn";
    backBtn.onclick = () => location.href = 'discussions.html';

    const topBar = document.createElement("div");
    topBar.className = "top-bar";
    topBar.appendChild(backBtn);
    topBar.appendChild(pageTitle);

    main.prepend(topBar);

    // Ask question section
    const askSection = document.createElement("section");
    askSection.className = "discussion-section";
    askSection.innerHTML = `
        <div class="discussion-card">
            <div class="card-header">
                <span class="timestamp">Just now</span>
                <span></span>
            </div>
            <p class="question-text">Ask a Question</p>
            <textarea id="new-question-text" placeholder="Ask something for ${major}..."></textarea>
            <button id="post-question-btn" class="post-reply">Post Question</button>
        </div>
    `;
    main.appendChild(askSection);

    const discussionSection = document.createElement("section");
    discussionSection.className = "discussion-section";
    main.appendChild(discussionSection);

    async function loadDiscussions() {
        discussionSection.innerHTML = "";

        try {
            const response = await fetch(`/api/discussions?major=${encodeURIComponent(major)}`);
            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to load discussions.");
                return;
            }

            const discussionData = result;

            if (discussionData.length === 0) {
                const emptyCard = document.createElement("div");
                emptyCard.className = "discussion-card";
                emptyCard.innerHTML = `
                    <div class="card-header">
                        <span class="timestamp">Just now</span>
                        <span class="fins-up">
                            <img src="../images/fin.png" alt="Shark Fin" class="fin-icon"> 0
                        </span>
                    </div>
                    <p class="question-text">No questions yet for ${major}.</p>
                `;
                discussionSection.appendChild(emptyCard);
                return;
            }

            discussionData.forEach(d => {
                const card = document.createElement("div");
                card.className = "discussion-card";

                const repliesHtml = (d.replies || [])
                    .map(r => `<div class="reply">${r.reply_text}</div>`)
                    .join("");

                card.innerHTML = `
                    <div class="card-header">
                        <span class="timestamp">${d.time}</span>
                        <span class="fins-up">
                            <img src="../images/fin.png" alt="Shark Fin" class="fin-icon"> ${d.fins_up || 0}
                        </span>
                    </div>

                    <p class="question-text">${d.title}</p>

                    <button class="reply-btn">${openDiscussionIds.has(d.id) ? "Hide Replies" : "View Replies"}</button>

                    <div class="reply-box ${openDiscussionIds.has(d.id) ? "" : "hidden"}">
                        <div class="existing-replies">
                            ${repliesHtml || '<div class="reply">No replies yet.</div>'}
                        </div>

                        <textarea placeholder="Write a reply..."></textarea>
                        <button class="post-reply">Post Reply</button>
                    </div>
                `;

                const replyBtn = card.querySelector(".reply-btn");
                const replyBox = card.querySelector(".reply-box");
                const postReplyBtn = card.querySelector(".post-reply");
                const textarea = card.querySelector("textarea");

                replyBtn.addEventListener("click", () => {
                    replyBox.classList.toggle("hidden");

                    if (replyBox.classList.contains("hidden")) {
                        openDiscussionIds.delete(d.id);
                        replyBtn.textContent = "View Replies";
                    } else {
                        openDiscussionIds.add(d.id);
                        replyBtn.textContent = "Hide Replies";
                    }
                });

                postReplyBtn.addEventListener("click", async () => {
                    const replyText = textarea.value.trim();

                    if (!replyText) {
                        alert("Please write a reply first.");
                        return;
                    }

                    try {
                        openDiscussionIds.add(d.id);

                        const response = await fetch("/api/replies", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({
                                discussion_id: d.id,
                                reply_text: replyText
                            })
                        });

                        const result = await response.json();

                        if (!response.ok) {
                            alert(result.error || "Failed to post reply.");
                            return;
                        }

                        textarea.value = "";
                        await loadDiscussions();

                    } catch (error) {
                        console.error("Reply error:", error);
                        alert("An error occurred while posting the reply.");
                    }
                });

                discussionSection.appendChild(card);
            });

        } catch (error) {
            console.error("Load discussions error:", error);
            alert("An error occurred while loading discussions.");
        }
    }

    document.getElementById("post-question-btn").addEventListener("click", async () => {
        const questionText = document.getElementById("new-question-text").value.trim();

        if (!questionText) {
            alert("Please write a question first.");
            return;
        }

        try {
            const response = await fetch("/api/discussions", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    major: major,
                    question: questionText
                })
            });

            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to create question.");
                return;
            }

            document.getElementById("new-question-text").value = "";
            openDiscussionIds.add(result.id);
            await loadDiscussions();

        } catch (error) {
            console.error("Create question error:", error);
            alert("An error occurred while creating the question.");
        }
    });

    loadDiscussions();
}
</script>
"""


def serve_discussions_with_runtime_script():
    file_path = os.path.join(UI_DIR, "discussions.html")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    # replace the original inline script block with the runtime one
    html = re.sub(
        r"<script>[\s\S]*?</script>\s*</body>",
        DISCUSSIONS_RUNTIME_SCRIPT + "\n</body>",
        html,
        count=1,
        flags=re.IGNORECASE
    )

    return Response(html, mimetype="text/html")


# --------------------------------------------------
# LOGIN PAGE
# --------------------------------------------------
@app.route("/")
def login():
    return send_from_directory(UI_DIR, "login.html")


# --------------------------------------------------
# HOME PAGE
# --------------------------------------------------
@app.route("/home")
@app.route("/home.html")
def home():
    if "user" not in session:
        return redirect("/")
    return send_from_directory(UI_DIR, "home.html")


# --------------------------------------------------
# DISCUSSIONS PAGE
# --------------------------------------------------
@app.route("/discussions")
@app.route("/discussions.html")
def discussions():
    if "user" not in session:
        return redirect("/")
    return serve_discussions_with_runtime_script()


# --------------------------------------------------
# TUTORS PAGE
# --------------------------------------------------
@app.route("/tutors")
@app.route("/tutors.html")
def tutors():
    if "user" not in session:
        return redirect("/")
    return send_from_directory(UI_DIR, "tutors.html")


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
    global next_discussion_id

    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data or not data.get("major") or not data.get("question"):
        return jsonify({"error": "Missing data"}), 400

    new_discussion = {
        "id": next_discussion_id,
        "major": data["major"],
        "title": data["question"],
        "time": "Just now",
        "fins_up": 1,
        "replies": []
    }

    discussions_data.append(new_discussion)
    next_discussion_id += 1
    save_data()

    return jsonify(new_discussion), 201


# --------------------------------------------------
# CREATE REPLY
# --------------------------------------------------
@app.route("/api/replies", methods=["POST"])
def create_reply():
    global next_reply_id

    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data or not data.get("discussion_id") or not data.get("reply_text"):
        return jsonify({"error": "Missing data"}), 400

    discussion_id = data["discussion_id"]

    new_reply = {
        "id": next_reply_id,
        "reply_text": data["reply_text"]
    }

    for discussion in discussions_data:
        if discussion["id"] == discussion_id:
            discussion["replies"].append(new_reply)
            next_reply_id += 1
            save_data()
            return jsonify(new_reply), 201

    return jsonify({"error": "Discussion not found"}), 404


# --------------------------------------------------
# START SERVER
# --------------------------------------------------
if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=5000, debug=True)