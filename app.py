from flask import Flask, send_from_directory, request, redirect, session, jsonify, Response
import os
import json
import re
import sqlite3
 
app = Flask(__name__)
app.secret_key = "sharknet_secret_key"
 
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UI_DIR = os.path.join(BASE_DIR, "UI")
 
DB = os.path.join(BASE_DIR, "sharknet.db")
 
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row  # lets you access columns by name
    return conn
 
# tutor routes still use this - keeping it so they don't crash
def save_data():
    pass
 
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
const selectedTutorRatings = {};
 
function createTutorReviewElement(review) {
    const reviewDiv = document.createElement("div");
    reviewDiv.className = "review";
    reviewDiv.textContent = `"${review.review_text}"`;
    return reviewDiv;
}
 
function ensureBookingBox(card) {
    let bookingBox = card.querySelector(".booking-box");
 
    if (!bookingBox) {
        bookingBox = document.createElement("div");
        bookingBox.className = "booking-box hidden";
        bookingBox.innerHTML = `
            <div class="booking-title"><strong>Available Sessions</strong></div>
            <div class="booking-slots"></div>
            <div class="booking-message"></div>
        `;
 
        const cardButtons = card.querySelector(".card-buttons");
        cardButtons.insertAdjacentElement("afterend", bookingBox);
    }
 
    return bookingBox;
}
 
function updateRatingText(card, average) {
    const ratingSpan = card.querySelector(".rating");
    ratingSpan.textContent = `⭐ ${average.toFixed(1)}`;
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
 
async function loadTutorRatings() {
    try {
        const response = await fetch("/api/tutors/ratings");
        const result = await response.json();
 
        if (!response.ok) {
            alert(result.error || "Failed to load tutor ratings.");
            return;
        }
 
        document.querySelectorAll(".tutor-card").forEach(card => {
            const tutorName = card.querySelector(".tutor-name").textContent.trim();
            const ratingInfo = result[tutorName];
 
            if (ratingInfo) {
                updateRatingText(card, ratingInfo.average);
            }
        });
 
    } catch (error) {
        console.error("Load tutor ratings error:", error);
        alert("An error occurred while loading tutor ratings.");
    }
}
 
async function renderBookingSlots(card, tutorName) {
    const bookingBox = ensureBookingBox(card);
    const slotsContainer = bookingBox.querySelector(".booking-slots");
    const bookingMessage = bookingBox.querySelector(".booking-message");
 
    slotsContainer.innerHTML = "";
    bookingMessage.textContent = "";
 
    try {
        const response = await fetch(`/api/tutors/availability?tutor_name=${encodeURIComponent(tutorName)}`);
        const result = await response.json();
 
        if (!response.ok) {
            bookingMessage.textContent = result.error || "Failed to load availability.";
            return;
        }
 
        if (!result.available_slots || result.available_slots.length === 0) {
            bookingMessage.textContent = "No open times right now.";
            return;
        }
 
        result.available_slots.forEach(slot => {
            const slotButton = document.createElement("button");
            slotButton.className = "booking-slot-btn";
            slotButton.textContent = slot;
 
            slotButton.addEventListener("click", async () => {
                try {
                    const bookResponse = await fetch("/api/tutors/bookings", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            tutor_name: tutorName,
                            slot: slot
                        })
                    });
 
                    const bookResult = await bookResponse.json();
 
                    if (!bookResponse.ok) {
                        bookingMessage.textContent = bookResult.error || "Failed to book session.";
                        return;
                    }
 
                    bookingMessage.textContent = `Booked: ${slot}`;
                    await renderBookingSlots(card, tutorName);
 
                } catch (error) {
                    console.error("Booking error:", error);
                    bookingMessage.textContent = "An error occurred while booking.";
                }
            });
 
            slotsContainer.appendChild(slotButton);
        });
 
    } catch (error) {
        console.error("Availability error:", error);
        bookingMessage.textContent = "An error occurred while loading availability.";
    }
}
 
document.querySelectorAll(".review-toggle").forEach(button => {
    button.addEventListener("click", () => {
        const reviewBox = button.closest(".tutor-card").querySelector(".review-box");
        reviewBox.classList.toggle("hidden");
        button.textContent = reviewBox.classList.contains("hidden") ? "View Reviews" : "Hide Reviews";
    });
});
 
document.querySelectorAll(".tutor-card").forEach(card => {
    const tutorName = card.querySelector(".tutor-name").textContent.trim();
    const stars = card.querySelectorAll(".star");
    const submitRatingBtn = card.querySelector(".submit-rating");
    const bookBtn = card.querySelector(".book-btn");
 
    let currentRating = 0;
 
    // Star hover/click behavior
    stars.forEach(star => {
        star.addEventListener("mouseover", () => {
            const val = parseInt(star.dataset.value);
            stars.forEach(s => s.classList.toggle("hovered", parseInt(s.dataset.value) <= val));
        });
 
        star.addEventListener("mouseout", () => {
            stars.forEach(s => s.classList.remove("hovered"));
            stars.forEach(s => s.classList.toggle("selected", parseInt(s.dataset.value) <= currentRating));
        });
 
        star.addEventListener("click", () => {
            currentRating = parseInt(star.dataset.value);
            selectedTutorRatings[tutorName] = currentRating;
            stars.forEach(s => s.classList.toggle("selected", parseInt(s.dataset.value) <= currentRating));
        });
    });
 
    // Rating submit button
    if (submitRatingBtn) {
    submitRatingBtn.addEventListener("click", async () => {
        const ratingValue = selectedTutorRatings[tutorName];
 
        if (!ratingValue) {
            alert("Please choose a star rating first.");
            return;
        }
 
        try {
            const response = await fetch("/api/tutors/ratings", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    tutor_name: tutorName,
                    rating: ratingValue
                })
            });
 
            const result = await response.json();
 
            if (!response.ok) {
                alert(result.error || "Failed to submit rating.");
                return;
            }
 
            updateRatingText(card, result.average);
 
        } catch (error) {
            console.error("Submit rating error:", error);
            alert("An error occurred while submitting the rating.");
        }
    });
}
 
    // Book session button
    if (bookBtn) {
        bookBtn.addEventListener("click", async () => {
            const bookingBox = ensureBookingBox(card);
            bookingBox.classList.toggle("hidden");
 
            if (!bookingBox.classList.contains("hidden")) {
                await renderBookingSlots(card, tutorName);
            }
        });
    }
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
loadTutorRatings();
</script>
"""
 
 
# --------------------------------------------------
# HTML INJECTION HELPERS
# --------------------------------------------------
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
# DISCUSSION ROUTES
# --------------------------------------------------
@app.route("/api/discussions", methods=["GET"])
def get_discussions():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    major = request.args.get("major")
    if not major:
        return jsonify({"error": "Major is required"}), 400
 
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM discussions WHERE major = ? ORDER BY created_at DESC",
        (major,)
    ).fetchall()
 
    result = []
    for row in rows:
        d = dict(row)
        replies = conn.execute(
            "SELECT * FROM replies WHERE discussion_id = ?", (d["id"],)
        ).fetchall()
        d["replies"] = [dict(r) for r in replies]
        d["time"] = d["created_at"]  # so the frontend still works
        result.append(d)
 
    conn.close()
    return jsonify(result), 200
 
@app.route("/api/discussions", methods=["POST"])
def create_discussion():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    data = request.get_json()
    if not data or not data.get("major") or not data.get("question"):
        return jsonify({"error": "Missing data"}), 400
 
    conn = get_db()
    # save the student email if we haven't seen them before
    conn.execute("INSERT OR IGNORE INTO students (email) VALUES (?)", (session["user"],))
    cur = conn.execute(
        "INSERT INTO discussions (major, title, author_email, fins_up) VALUES (?, ?, ?, 0)",
        (data["major"], data["question"], session["user"])
    )
    conn.commit()
 
    new_id = cur.lastrowid
    conn.close()
 
    return jsonify({"id": new_id, "title": data["question"], "time": "Just now", "fins_up": 0, "replies": []}), 201
 
 
@app.route("/api/discussions/toggle_like", methods=["POST"])
def toggle_discussion_like():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    data = request.get_json()
    if not data or not data.get("discussion_id"):
        return jsonify({"error": "discussion_id is required"}), 400
 
    discussion_id = data["discussion_id"]
 
    conn = get_db()
    row = conn.execute("SELECT * FROM discussions WHERE id = ?", (discussion_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Discussion not found"}), 404
 
    new_fins = (row["fins_up"] or 0) + 1
    conn.execute("UPDATE discussions SET fins_up = ? WHERE id = ?", (new_fins, discussion_id))
    conn.commit()
    conn.close()
 
    return jsonify({"id": discussion_id, "fins_up": new_fins}), 200
 
 
@app.route("/api/discussions/<int:discussion_id>", methods=["DELETE"])
def delete_discussion(discussion_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    user_email = session["user"]
 
    conn = get_db()
    row = conn.execute("SELECT * FROM discussions WHERE id = ?", (discussion_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Discussion not found"}), 404
 
    if row["author_email"] != user_email:
        conn.close()
        return jsonify({"error": "You can only delete your own post"}), 403
 
    conn.execute("DELETE FROM replies WHERE discussion_id = ?", (discussion_id,))
    conn.execute("DELETE FROM discussions WHERE id = ?", (discussion_id,))
    conn.commit()
    conn.close()
 
    return jsonify({"success": True}), 200
 
 
@app.route("/api/replies", methods=["POST"])
def create_reply():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    data = request.get_json()
    if not data or not data.get("discussion_id") or not data.get("reply_text"):
        return jsonify({"error": "Missing data"}), 400
 
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO replies (discussion_id, reply_text, author_email) VALUES (?, ?, ?)",
        (data["discussion_id"], data["reply_text"], session["user"])
    )
    conn.commit()
    conn.close()
 
    return jsonify({"id": cur.lastrowid, "reply_text": data["reply_text"]}), 201
 
 
@app.route("/api/replies/toggle_like", methods=["POST"])
def toggle_reply_like():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    data = request.get_json()
    if not data or not data.get("reply_id"):
        return jsonify({"error": "reply_id is required"}), 400
 
    reply_id = data["reply_id"]
 
    conn = get_db()
    row = conn.execute("SELECT * FROM replies WHERE id = ?", (reply_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Reply not found"}), 404
 
    new_fins = (row["fins_up"] or 0) + 1
    conn.execute("UPDATE replies SET fins_up = ? WHERE id = ?", (new_fins, reply_id))
    conn.commit()
    conn.close()
 
    return jsonify({"id": reply_id, "fins_up": new_fins}), 200
 
 
@app.route("/api/replies/<int:reply_id>", methods=["DELETE"])
def delete_reply(reply_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    user_email = session["user"]
 
    conn = get_db()
    row = conn.execute("SELECT * FROM replies WHERE id = ?", (reply_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Reply not found"}), 404
 
    if row["author_email"] != user_email:
        conn.close()
        return jsonify({"error": "You can only delete your own reply"}), 403
 
    conn.execute("DELETE FROM replies WHERE id = ?", (reply_id,))
    conn.commit()
    conn.close()
 
    return jsonify({"success": True}), 200
 
 
# --------------------------------------------------
# TUTOR REVIEW ROUTES
# --------------------------------------------------
@app.route("/api/tutors/reviews", methods=["GET"])
def get_tutor_reviews():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    return jsonify(tutor_reviews), 200
 
 
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
# TUTOR RATING ROUTES
# --------------------------------------------------
@app.route("/api/tutors/ratings", methods=["GET"])
def get_tutor_ratings():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    rating_summary = {}
 
    for tutor_name, info in tutor_rating_data.items():
        total = float(info.get("total", 0))
        count = int(info.get("count", 0))
        average = total / count if count > 0 else 0
 
        rating_summary[tutor_name] = {
            "average": average,
            "count": count
        }
 
    return jsonify(rating_summary), 200
 
 
@app.route("/api/tutors/ratings", methods=["POST"])
def submit_tutor_rating():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    data = request.get_json()
 
    if not data or not data.get("tutor_name") or data.get("rating") is None:
        return jsonify({"error": "Missing data"}), 400
 
    tutor_name = data["tutor_name"].strip()
    user_email = session["user"]
 
    try:
        rating_value = int(data["rating"])
    except (TypeError, ValueError):
        return jsonify({"error": "Rating must be a number"}), 400
 
    if rating_value < 1 or rating_value > 5:
        return jsonify({"error": "Rating must be between 1 and 5"}), 400
 
    if tutor_name not in tutor_rating_data:
        tutor_rating_data[tutor_name] = {
            "total": 0,
            "count": 0,
            "by_user": {}
        }
 
    info = tutor_rating_data[tutor_name]
    by_user = info.setdefault("by_user", {})
 
    # If this user already rated this tutor, replace old rating
    if user_email in by_user:
        old_rating = by_user[user_email]
        info["total"] = float(info.get("total", 0)) - old_rating + rating_value
        by_user[user_email] = rating_value
    else:
        info["total"] = float(info.get("total", 0)) + rating_value
        info["count"] = int(info.get("count", 0)) + 1
        by_user[user_email] = rating_value
 
    average = info["total"] / info["count"] if info["count"] > 0 else 0
    save_data()
 
    return jsonify({
        "tutor_name": tutor_name,
        "average": average,
        "count": info["count"],
        "your_rating": rating_value
    }), 200
 
 
# --------------------------------------------------
# TUTOR AVAILABILITY / BOOKING ROUTES
# --------------------------------------------------
@app.route("/api/tutors/availability", methods=["GET"])
def get_tutor_availability():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    tutor_name = request.args.get("tutor_name", "").strip()
 
    if not tutor_name:
        return jsonify({"error": "tutor_name is required"}), 400
 
    available_slots = tutor_availability.get(tutor_name, [])
 
    return jsonify({
        "tutor_name": tutor_name,
        "available_slots": available_slots
    }), 200
 
 
@app.route("/api/tutors/bookings", methods=["POST"])
def create_tutor_booking():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
 
    data = request.get_json()
 
    if not data or not data.get("tutor_name") or not data.get("slot"):
        return jsonify({"error": "Missing data"}), 400
 
    tutor_name = data["tutor_name"].strip()
    slot = data["slot"].strip()
    user_email = session["user"]
 
    if tutor_name not in tutor_availability:
        return jsonify({"error": "Tutor not found"}), 404
 
    if slot not in tutor_availability[tutor_name]:
        return jsonify({"error": "That time is no longer available"}), 400
 
    # Remove booked slot from available list
    tutor_availability[tutor_name].remove(slot)
 
    # Save booking
    tutor_bookings.setdefault(tutor_name, []).append({
        "student_email": user_email,
        "slot": slot
    })
 
    save_data()
 
    return jsonify({
        "message": "Session booked successfully",
        "tutor_name": tutor_name,
        "slot": slot
    }), 201
 
 
# --------------------------------------------------
# START SERVER
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
