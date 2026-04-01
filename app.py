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
tutor_reviews = {}
next_tutor_review_id = 1


def get_default_tutor_reviews():
    return {
        "Jane Doe": [
            {
                "id": 1,
                "review_text": "Super clear explanations!",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 2,
                "review_text": "Helped me debug my projects.",
                "author_email": "",
                "time": "Just now"
            }
        ],
        "Alice Susan": [
            {
                "id": 3,
                "review_text": "Helped me understand SQL queries.",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 4,
                "review_text": "Super friendly and patient.",
                "author_email": "",
                "time": "Just now"
            }
        ],
        "Michael Brown": [
            {
                "id": 5,
                "review_text": "Explains concepts in a really understandable way.",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 6,
                "review_text": "Great study tips for exams!",
                "author_email": "",
                "time": "Just now"
            }
        ],
        "Emily Lee": [
            {
                "id": 7,
                "review_text": "Helped me improve my research paper.",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 8,
                "review_text": "Very knowledgeable and patient.",
                "author_email": "",
                "time": "Just now"
            }
        ],
        "John Smith": [
            {
                "id": 9,
                "review_text": "Great explanations for complex engineering topics.",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 10,
                "review_text": "Helped me understand lab experiments.",
                "author_email": "",
                "time": "Just now"
            }
        ],
        "Samantha Green": [
            {
                "id": 11,
                "review_text": "Explains finance concepts clearly.",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 12,
                "review_text": "Helped me with my marketing assignment.",
                "author_email": "",
                "time": "Just now"
            }
        ],
        "David Wilson": [
            {
                "id": 13,
                "review_text": "Very patient and thorough explanations.",
                "author_email": "",
                "time": "Just now"
            },
            {
                "id": 14,
                "review_text": "Helped me prepare for exams effectively.",
                "author_email": "",
                "time": "Just now"
            }
        ]
    }


def save_data():
    data = {
        "discussions_data": discussions_data,
        "next_discussion_id": next_discussion_id,
        "next_reply_id": next_reply_id,
        "tutor_reviews": tutor_reviews,
        "next_tutor_review_id": next_tutor_review_id
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def migrate_loaded_data():
    global discussions_data, tutor_reviews, next_tutor_review_id

    for discussion in discussions_data:
        if "author_email" not in discussion:
            discussion["author_email"] = ""
        if "liked_by" not in discussion:
            discussion["liked_by"] = []
        if "fins_up" not in discussion:
            discussion["fins_up"] = len(discussion["liked_by"])
        if "replies" not in discussion:
            discussion["replies"] = []

        for reply in discussion.get("replies", []):
            if "author_email" not in reply:
                reply["author_email"] = ""
            if "liked_by" not in reply:
                reply["liked_by"] = []
            if "fins_up" not in reply:
                reply["fins_up"] = len(reply["liked_by"])

    default_reviews = get_default_tutor_reviews()

    if not isinstance(tutor_reviews, dict):
        tutor_reviews = default_reviews
    else:
        for tutor_name, reviews in default_reviews.items():
            if tutor_name not in tutor_reviews:
                tutor_reviews[tutor_name] = reviews

    max_id = 0
    for review_list in tutor_reviews.values():
        for review in review_list:
            if "id" not in review:
                max_id += 1
                review["id"] = max_id
            else:
                max_id = max(max_id, review["id"])

            if "review_text" not in review:
                review["review_text"] = ""
            if "author_email" not in review:
                review["author_email"] = ""
            if "time" not in review:
                review["time"] = "Just now"

    if next_tutor_review_id <= max_id:
        next_tutor_review_id = max_id + 1


def load_data():
    global discussions_data, next_discussion_id, next_reply_id, tutor_reviews, next_tutor_review_id

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            discussions_data = data.get("discussions_data", [])
            next_discussion_id = data.get("next_discussion_id", 1)
            next_reply_id = data.get("next_reply_id", 1)
            tutor_reviews = data.get("tutor_reviews", get_default_tutor_reviews())
            next_tutor_review_id = data.get("next_tutor_review_id", 1)
            migrate_loaded_data()
    else:
        discussions_data = []
        next_discussion_id = 1
        next_reply_id = 1
        tutor_reviews = get_default_tutor_reviews()
        next_tutor_review_id = 15


# --------------------------------------------------
# RUNTIME SCRIPT INJECTION FOR ORIGINAL discussions.html
# --------------------------------------------------
DISCUSSIONS_RUNTIME_SCRIPT = r"""
<script>
const params = new URLSearchParams(window.location.search);
const major = params.get("major");
const currentUserEmail = {{CURRENT_USER_EMAIL_JSON}};

const openDiscussionIds = new Set();

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

function createReplyElement(reply, discussionId) {
    const replyDiv = document.createElement("div");
    replyDiv.className = "reply";
    replyDiv.dataset.replyId = reply.id;

    const replyText = document.createElement("span");
    replyText.className = "reply-text";
    replyText.textContent = reply.reply_text;

    const finsSpan = document.createElement("span");
    finsSpan.className = "fins-up reply-fins-up";
    finsSpan.dataset.replyId = reply.id;
    finsSpan.style.cursor = "pointer";
    finsSpan.style.marginLeft = "10px";
    finsSpan.innerHTML = `<img src="../images/fin.png" alt="Shark Fin" class="fin-icon"> ${reply.fins_up || 0}`;

    finsSpan.addEventListener("click", async () => {
        try {
            const response = await fetch("/api/replies/toggle_like", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    discussion_id: discussionId,
                    reply_id: reply.id
                })
            });

            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to update reply like.");
                return;
            }

            finsSpan.innerHTML = `<img src="../images/fin.png" alt="Shark Fin" class="fin-icon"> ${result.fins_up}`;

        } catch (error) {
            console.error("Reply like error:", error);
            alert("An error occurred while updating the reply like.");
        }
    });

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "delete-reply-btn";
    deleteBtn.dataset.replyId = reply.id;
    deleteBtn.textContent = "Delete Reply";

    deleteBtn.addEventListener("click", async () => {
        try {
            const response = await fetch(`/api/replies/${reply.id}`, {
                method: "DELETE"
            });

            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to delete reply.");
                return;
            }

            replyDiv.remove();

            const repliesContainer = replyDiv.parentElement;
            if (repliesContainer && repliesContainer.children.length === 0) {
                repliesContainer.innerHTML = '<div class="reply no-replies-placeholder">No replies yet.</div>';
            }

        } catch (error) {
            console.error("Delete reply error:", error);
            alert("An error occurred while deleting the reply.");
        }
    });

    replyDiv.appendChild(replyText);
    replyDiv.appendChild(finsSpan);
    replyDiv.appendChild(deleteBtn);

    return replyDiv;
}

function createDiscussionCard(d) {
    const card = document.createElement("div");
    card.className = "discussion-card";
    card.dataset.discussionId = d.id;

    const isOpen = openDiscussionIds.has(d.id);

    card.innerHTML = `
        <div class="card-header">
            <span class="timestamp">${escapeHtml(d.time)}</span>
            <span class="fins-up discussion-fins-up" data-discussion-id="${d.id}" style="cursor:pointer;">
                <img src="../images/fin.png" alt="Shark Fin" class="fin-icon"> ${d.fins_up || 0}
            </span>
        </div>

        <p class="question-text">${escapeHtml(d.title)}</p>

        <div class="card-actions-row">
            <button class="reply-btn">${isOpen ? "Hide Replies" : "View Replies"}</button>
            <button class="delete-btn">Delete Post</button>
        </div>

        <div class="reply-box ${isOpen ? "" : "hidden"}">
            <div class="existing-replies"></div>
            <textarea placeholder="Write a reply..."></textarea>
            <button class="post-reply">Post Reply</button>
        </div>
    `;

    const discussionFinsUp = card.querySelector(".discussion-fins-up");
    const replyBtn = card.querySelector(".reply-btn");
    const deleteBtn = card.querySelector(".delete-btn");
    const replyBox = card.querySelector(".reply-box");
    const existingReplies = card.querySelector(".existing-replies");
    const textarea = card.querySelector("textarea");
    const postReplyBtn = card.querySelector(".post-reply");

    if (d.author_email && d.author_email !== currentUserEmail) {
        deleteBtn.style.display = "none";
    }

    if (d.replies && d.replies.length > 0) {
        d.replies.forEach(reply => {
            existingReplies.appendChild(createReplyElement(reply, d.id));
        });
    } else {
        existingReplies.innerHTML = '<div class="reply no-replies-placeholder">No replies yet.</div>';
    }

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

    discussionFinsUp.addEventListener("click", async () => {
        try {
            const response = await fetch("/api/discussions/toggle_like", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    discussion_id: d.id
                })
            });

            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to update like.");
                return;
            }

            discussionFinsUp.innerHTML = `<img src="../images/fin.png" alt="Shark Fin" class="fin-icon"> ${result.fins_up}`;

        } catch (error) {
            console.error("Discussion like error:", error);
            alert("An error occurred while updating the like.");
        }
    });

    deleteBtn.addEventListener("click", async () => {
        try {
            const response = await fetch(`/api/discussions/${d.id}`, {
                method: "DELETE"
            });

            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to delete post.");
                return;
            }

            openDiscussionIds.delete(d.id);
            card.remove();

            const discussionSection = document.querySelector(".discussion-section.discussion-list");
            if (discussionSection && discussionSection.children.length === 0) {
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
            }

        } catch (error) {
            console.error("Delete post error:", error);
            alert("An error occurred while deleting the post.");
        }
    });

    postReplyBtn.addEventListener("click", async () => {
        const replyText = textarea.value.trim();

        if (!replyText) {
            alert("Please write a reply first.");
            return;
        }

        try {
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

            const placeholder = existingReplies.querySelector(".no-replies-placeholder");
            if (placeholder) {
                placeholder.remove();
            }

            existingReplies.appendChild(createReplyElement(result, d.id));
            textarea.value = "";

            openDiscussionIds.add(d.id);
            replyBox.classList.remove("hidden");
            replyBtn.textContent = "Hide Replies";

        } catch (error) {
            console.error("Reply error:", error);
            alert("An error occurred while posting the reply.");
        }
    });

    return card;
}

if (major) {
    const main = document.querySelector("main");
    document.getElementById("majors-section").style.display = "none";

    const pageTitle = document.createElement("h2");
    pageTitle.textContent = major + " Discussions";
    pageTitle.className = "section-title";

    const backBtn = document.createElement("button");
    backBtn.textContent = "← Back";
    backBtn.className = "back-btn";
    backBtn.onclick = () => location.href = "discussions.html";

    const topBar = document.createElement("div");
    topBar.className = "top-bar";
    topBar.appendChild(backBtn);
    topBar.appendChild(pageTitle);

    main.prepend(topBar);

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
    discussionSection.className = "discussion-section discussion-list";
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
                discussionSection.appendChild(createDiscussionCard(d));
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

            const emptyCard = discussionSection.querySelector(".discussion-card");
            if (
                emptyCard &&
                emptyCard.querySelector(".question-text") &&
                emptyCard.querySelector(".question-text").textContent === `No questions yet for ${major}.`
            ) {
                discussionSection.innerHTML = "";
            }

            openDiscussionIds.add(result.id);
            discussionSection.prepend(createDiscussionCard(result));

        } catch (error) {
            console.error("Create question error:", error);
            alert("An error occurred while creating the question.");
        }
    });

    loadDiscussions();
}
</script>
"""

# --------------------------------------------------
# RUNTIME SCRIPT INJECTION FOR ORIGINAL tutors.html
# --------------------------------------------------
TUTORS_RUNTIME_SCRIPT = r"""
<script>
function createTutorReviewElement(review) {
    const reviewDiv = document.createElement("div");
    reviewDiv.className = "review";
    reviewDiv.textContent = `"${review.review_text}"`;
    return reviewDiv;
}

async function loadTutorReviews() {
    try {
        const response = await fetch("/api/tutors/reviews");
        const result = await response.json();

        if (!response.ok) {
            alert(result.error || "Failed to load tutor reviews.");
            return;
        }

        document.querySelectorAll(".tutor-card").forEach(card => {
            const tutorName = card.querySelector(".tutor-name").textContent.trim();
            const existingReviews = card.querySelector(".existing-reviews");
            const reviewList = result[tutorName] || [];

            existingReviews.innerHTML = "";

            reviewList.forEach(review => {
                existingReviews.appendChild(createTutorReviewElement(review));
            });
        });

    } catch (error) {
        console.error("Load tutor reviews error:", error);
        alert("An error occurred while loading tutor reviews.");
    }
}

document.querySelectorAll(".review-toggle").forEach(button => {
    button.addEventListener("click", () => {
        const reviewBox = button.closest(".tutor-card").querySelector(".review-box");
        reviewBox.classList.toggle("hidden");
        button.textContent = reviewBox.classList.contains("hidden") ? "View Reviews" : "Hide Reviews";
    });
});

document.querySelectorAll(".post-review").forEach(button => {
    button.addEventListener("click", async () => {
        const tutorCard = button.closest(".tutor-card");
        const tutorName = tutorCard.querySelector(".tutor-name").textContent.trim();
        const textarea = tutorCard.querySelector("textarea");
        const existingReviews = tutorCard.querySelector(".existing-reviews");
        const reviewText = textarea.value.trim();

        if (!reviewText) {
            alert("Please write a review first.");
            return;
        }

        try {
            const response = await fetch("/api/tutors/reviews", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    tutor_name: tutorName,
                    review_text: reviewText
                })
            });

            const result = await response.json();

            if (!response.ok) {
                alert(result.error || "Failed to post review.");
                return;
            }

            existingReviews.appendChild(createTutorReviewElement(result));
            textarea.value = "";

        } catch (error) {
            console.error("Post tutor review error:", error);
            alert("An error occurred while posting the review.");
        }
    });
});

loadTutorReviews();
</script>
"""


def serve_discussions_with_runtime_script():
    file_path = os.path.join(UI_DIR, "discussions.html")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    current_user_email_json = json.dumps(session.get("user", ""))

    injected_script = DISCUSSIONS_RUNTIME_SCRIPT.replace(
        "{{CURRENT_USER_EMAIL_JSON}}",
        current_user_email_json
    )

    html = re.sub(
        r"<script>[\s\S]*?</script>\s*</body>",
        injected_script + "\n</body>",
        html,
        count=1,
        flags=re.IGNORECASE
    )

    return Response(html, mimetype="text/html")


def serve_tutors_with_runtime_script():
    file_path = os.path.join(UI_DIR, "tutors.html")

    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    html = re.sub(
        r"<script>[\s\S]*?</script>\s*</body>",
        TUTORS_RUNTIME_SCRIPT + "\n</body>",
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
    return serve_tutors_with_runtime_script()


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

    user_email = session["user"]

    new_discussion = {
        "id": next_discussion_id,
        "major": data["major"],
        "title": data["question"],
        "time": "Just now",
        "author_email": user_email,
        "liked_by": [],
        "fins_up": 0,
        "replies": []
    }

    discussions_data.append(new_discussion)
    next_discussion_id += 1
    save_data()

    return jsonify(new_discussion), 201


# --------------------------------------------------
# TOGGLE LIKE FOR DISCUSSION
# --------------------------------------------------
@app.route("/api/discussions/toggle_like", methods=["POST"])
def toggle_discussion_like():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data or not data.get("discussion_id"):
        return jsonify({"error": "discussion_id is required"}), 400

    discussion_id = data["discussion_id"]
    user_email = session["user"]

    for discussion in discussions_data:
        if discussion["id"] == discussion_id:
            liked_by = discussion.setdefault("liked_by", [])

            if user_email in liked_by:
                liked_by.remove(user_email)
            else:
                liked_by.append(user_email)

            discussion["fins_up"] = len(liked_by)
            save_data()

            return jsonify({
                "id": discussion["id"],
                "fins_up": discussion["fins_up"],
                "liked": user_email in liked_by
            }), 200

    return jsonify({"error": "Discussion not found"}), 404


# --------------------------------------------------
# DELETE DISCUSSION
# --------------------------------------------------
@app.route("/api/discussions/<int:discussion_id>", methods=["DELETE"])
def delete_discussion(discussion_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = session["user"]

    for index, discussion in enumerate(discussions_data):
        if discussion["id"] == discussion_id:
            if discussion.get("author_email") != user_email:
                return jsonify({"error": "You can only delete your own post"}), 403

            discussions_data.pop(index)
            save_data()
            return jsonify({"success": True}), 200

    return jsonify({"error": "Discussion not found"}), 404


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
    user_email = session["user"]

    new_reply = {
        "id": next_reply_id,
        "reply_text": data["reply_text"],
        "author_email": user_email,
        "liked_by": [],
        "fins_up": 0
    }

    for discussion in discussions_data:
        if discussion["id"] == discussion_id:
            discussion["replies"].append(new_reply)
            next_reply_id += 1
            save_data()
            return jsonify(new_reply), 201

    return jsonify({"error": "Discussion not found"}), 404


# --------------------------------------------------
# TOGGLE LIKE FOR REPLY
# --------------------------------------------------
@app.route("/api/replies/toggle_like", methods=["POST"])
def toggle_reply_like():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data or not data.get("discussion_id") or not data.get("reply_id"):
        return jsonify({"error": "discussion_id and reply_id are required"}), 400

    discussion_id = data["discussion_id"]
    reply_id = data["reply_id"]
    user_email = session["user"]

    for discussion in discussions_data:
        if discussion["id"] == discussion_id:
            for reply in discussion.get("replies", []):
                if reply["id"] == reply_id:
                    liked_by = reply.setdefault("liked_by", [])

                    if user_email in liked_by:
                        liked_by.remove(user_email)
                    else:
                        liked_by.append(user_email)

                    reply["fins_up"] = len(liked_by)
                    save_data()

                    return jsonify({
                        "id": reply["id"],
                        "fins_up": reply["fins_up"],
                        "liked": user_email in liked_by
                    }), 200

            return jsonify({"error": "Reply not found"}), 404

    return jsonify({"error": "Discussion not found"}), 404


# --------------------------------------------------
# DELETE REPLY
# --------------------------------------------------
@app.route("/api/replies/<int:reply_id>", methods=["DELETE"])
def delete_reply(reply_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_email = session["user"]

    for discussion in discussions_data:
        replies = discussion.get("replies", [])
        for index, reply in enumerate(replies):
            if reply["id"] == reply_id:
                if reply.get("author_email") != user_email:
                    return jsonify({"error": "You can only delete your own reply"}), 403

                replies.pop(index)
                save_data()
                return jsonify({"success": True}), 200

    return jsonify({"error": "Reply not found"}), 404


# --------------------------------------------------
# GET TUTOR REVIEWS
# --------------------------------------------------
@app.route("/api/tutors/reviews", methods=["GET"])
def get_tutor_reviews():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify(tutor_reviews), 200


# --------------------------------------------------
# CREATE TUTOR REVIEW
# --------------------------------------------------
@app.route("/api/tutors/reviews", methods=["POST"])
def create_tutor_review():
    global next_tutor_review_id

    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()

    if not data or not data.get("tutor_name") or not data.get("review_text"):
        return jsonify({"error": "Missing data"}), 400

    tutor_name = data["tutor_name"].strip()
    review_text = data["review_text"].strip()

    if not tutor_name or not review_text:
        return jsonify({"error": "Missing data"}), 400

    new_review = {
        "id": next_tutor_review_id,
        "review_text": review_text,
        "author_email": session["user"],
        "time": "Just now"
    }

    if tutor_name not in tutor_reviews:
        tutor_reviews[tutor_name] = []

    tutor_reviews[tutor_name].append(new_review)
    next_tutor_review_id += 1
    save_data()

    return jsonify(new_review), 201


# --------------------------------------------------
# START SERVER
# --------------------------------------------------
if __name__ == "__main__":
    load_data()
    app.run(host="0.0.0.0", port=5000, debug=True)