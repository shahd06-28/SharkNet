from flask import Flask, send_from_directory, request, redirect, session, jsonify, Response
import os
import json
import re
import sqlite3
import smtplib
import mimetypes
from email.message import EmailMessage
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "sharknet_secret_key"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UI_DIR = os.path.join(BASE_DIR, "UI")
DB = os.path.join(BASE_DIR, "sharknet.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
TUTOR_REQUEST_EMAILS = [
    "nj616@mynsu.nova.edu",
    "mm6386@mynsu.nova.edu",
    "sd2383@mynsu.nova.edu"
]

os.makedirs(UPLOAD_DIR, exist_ok=True)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def get_public_user_id(email):
    if not email:
        return "Anonymous"
    return email.strip().split("@")[0]


def build_display_identity(email, visibility_choice):
    if visibility_choice == "id":
        return {
            "post_visibility": "id",
            "author_display": get_public_user_id(email)
        }
    return {
        "post_visibility": "anonymous",
        "author_display": "Anonymous"
    }


def send_tutor_request_email(request_record, saved_resume_path=None):
    smtp_host = os.environ.get("SHARKNET_SMTP_HOST", "")
    smtp_port = int(os.environ.get("SHARKNET_SMTP_PORT", "587"))
    smtp_user = os.environ.get("SHARKNET_SMTP_USER", "")
    smtp_password = os.environ.get("SHARKNET_SMTP_PASSWORD", "")
    smtp_use_tls = os.environ.get("SHARKNET_SMTP_USE_TLS", "true").lower() != "false"
    sender = os.environ.get("SHARKNET_SMTP_FROM", smtp_user)

    if not smtp_host or not sender:
        return False, "SMTP is not configured. Submission was saved locally."

    msg = EmailMessage()
    msg["Subject"] = f"SharkNet Tutor Request - {request_record.get('name', 'Unknown User')}"
    msg["From"] = sender
    msg["To"] = ", ".join(TUTOR_REQUEST_EMAILS)

    body = (
        "New tutor request submitted.\n\n"
        f"Name: {request_record.get('name', '')}\n"
        f"Email: {request_record.get('email', '')}\n"
        f"Major: {request_record.get('major', '')}\n"
        f"Year: {request_record.get('year', '')}\n"
        f"Subjects: {request_record.get('subjects', '')}\n"
        f"Phone: {request_record.get('phone', '')}\n"
        f"Availability: {request_record.get('availability', '')}\n\n"
        "Experience / Comment:\n"
        f"{request_record.get('experience', '')}\n"
    )
    msg.set_content(body)

    if saved_resume_path and os.path.exists(saved_resume_path):
        mime_type, _ = mimetypes.guess_type(saved_resume_path)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        with open(saved_resume_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=os.path.basename(saved_resume_path)
            )

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_use_tls:
                server.starttls()
            if smtp_user:
                server.login(smtp_user, smtp_password)
            server.send_message(msg)
        return True, "Tutor request email sent."
    except Exception as exc:
        return False, f"Tutor request was saved, but email sending failed: {exc}"

# --------------------------------------------------
# RUNTIME SCRIPT INJECTION FOR ORIGINAL home.html
# --------------------------------------------------
HOME_RUNTIME_SCRIPT = r"""
<script>
document.addEventListener("DOMContentLoaded", () => {
    const discussionTargets = {
        "Campus Conversations": "/discussions.html?major=Campus",
        "Computer Science": "/discussions.html?major=Computer%20Science",
        "Psychology": "/discussions.html?major=Psychology"
    };

    const tutorTargets = {
        "Jane Doe": "/tutors.html?tutor=Jane%20Doe",
        "John Smith": "/tutors.html?tutor=John%20Smith",
        "Emily Lee": "/tutors.html?tutor=Emily%20Lee"
    };

    document.querySelectorAll(".featured-section .card").forEach(card => {
        const titleEl = card.querySelector("h3");
        const buttonEl = card.querySelector("button");
        if (!titleEl || !buttonEl) return;

        const title = titleEl.textContent.trim();
        const target = discussionTargets[title] || tutorTargets[title];
        if (!target) return;

        const go = () => { window.location.href = target; };
        card.style.cursor = "pointer";
        card.addEventListener("click", go);
        buttonEl.onclick = null;
        buttonEl.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            go();
        });
    });
});
</script>
"""

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

function addIdentityModalStyles() {
    if (document.getElementById("identity-modal-styles")) return;

    const style = document.createElement("style");
    style.id = "identity-modal-styles";
    style.textContent = `
        .identity-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }

        .identity-modal-box {
            background: white;
            border-radius: 14px;
            padding: 22px;
            width: min(92vw, 380px);
            box-shadow: 0 10px 35px rgba(0,0,0,0.2);
            text-align: center;
        }

        .identity-modal-box h3 {
            margin: 0 0 10px 0;
        }

        .identity-modal-box p {
            margin: 0 0 18px 0;
            color: #444;
        }

        .identity-modal-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .identity-choice-btn {
            border: none;
            padding: 10px 16px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
        }

        .identity-choice-btn.show-id {
            background: #0d6efd;
            color: white;
        }

        .identity-choice-btn.anonymous {
            background: #6c757d;
            color: white;
        }

        .identity-choice-btn.cancel {
            background: #e9ecef;
            color: #222;
        }

        .author-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            background: #eef3ff;
            font-size: 12px;
            font-weight: 600;
            color: #234;
            margin-left: 8px;
        }

        .reply-meta {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 6px;
        }

        .reply-author {
            font-size: 12px;
            font-weight: 600;
            color: #345;
            background: #eef3ff;
            padding: 3px 9px;
            border-radius: 999px;
        }

        .discussion-author-row {
            margin-top: 4px;
            margin-bottom: 8px;
        }
    `;
    document.head.appendChild(style);
}

function choosePostingIdentity() {
    addIdentityModalStyles();

    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "identity-modal-overlay";

        const box = document.createElement("div");
        box.className = "identity-modal-box";
        box.innerHTML = `
            <h3>Choose how to post</h3>
            <p>Do you want to show your NSU ID or stay anonymous?</p>
            <div class="identity-modal-actions">
                <button class="identity-choice-btn show-id">Show ID</button>
                <button class="identity-choice-btn anonymous">Anonymous</button>
                <button class="identity-choice-btn cancel">Cancel</button>
            </div>
        `;

        overlay.appendChild(box);
        document.body.appendChild(overlay);

        box.querySelector(".show-id").addEventListener("click", () => {
            overlay.remove();
            resolve("id");
        });

        box.querySelector(".anonymous").addEventListener("click", () => {
            overlay.remove();
            resolve("anonymous");
        });

        box.querySelector(".cancel").addEventListener("click", () => {
            overlay.remove();
            resolve(null);
        });

        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(null);
            }
        });
    });
}

function createReplyElement(reply, discussionId) {
    const replyDiv = document.createElement("div");
    replyDiv.className = "reply";
    replyDiv.dataset.replyId = reply.id;

    const metaRow = document.createElement("div");
    metaRow.className = "reply-meta";

    const replyAuthor = document.createElement("span");
    replyAuthor.className = "reply-author";
    replyAuthor.textContent = reply.author_display || "Anonymous";

    metaRow.appendChild(replyAuthor);

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

    if (reply.author_email && reply.author_email !== currentUserEmail) {
        deleteBtn.style.display = "none";
    }

    replyDiv.appendChild(metaRow);
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

        <div class="discussion-author-row">
            <span class="author-chip">${escapeHtml(d.author_display || "Anonymous")}</span>
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
                    <div class="discussion-author-row">
                        <span class="author-chip">System</span>
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

        const visibilityChoice = await choosePostingIdentity();

        if (!visibilityChoice) {
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
                    reply_text: replyText,
                    visibility_choice: visibilityChoice
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

    const campusSection = document.getElementById("campus-conversations");
    if (campusSection) {
        campusSection.style.display = "none";
    }

    const majorsSection = document.getElementById("majors-section");
    if (majorsSection) {
        majorsSection.style.display = "none";
    }

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
                    <div class="discussion-author-row">
                        <span class="author-chip">System</span>
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

        const visibilityChoice = await choosePostingIdentity();

        if (!visibilityChoice) {
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
                    question: questionText,
                    visibility_choice: visibilityChoice
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
const currentUserEmail = {{CURRENT_USER_EMAIL_JSON}};

function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
}

function addRuntimeStyles() {
    if (document.getElementById("sharknet-runtime-styles")) return;

    const style = document.createElement("style");
    style.id = "sharknet-runtime-styles";
    style.textContent = `
        .identity-modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.45);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        .identity-modal-box {
            background: white;
            border-radius: 14px;
            padding: 22px;
            width: min(92vw, 420px);
            box-shadow: 0 10px 35px rgba(0,0,0,0.2);
            text-align: center;
        }
        .identity-modal-box h3 { margin: 0 0 10px 0; }
        .identity-modal-box p { margin: 0 0 18px 0; color: #444; }
        .identity-modal-actions {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .identity-choice-btn {
            border: none;
            padding: 10px 16px;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
        }
        .identity-choice-btn.show-id { background: #0d6efd; color: white; }
        .identity-choice-btn.anonymous { background: #6c757d; color: white; }
        .identity-choice-btn.cancel { background: #e9ecef; color: #222; }
        .review-meta {
            font-size: 12px;
            font-weight: 600;
            color: #345;
            margin-top: 4px;
        }
        .review-delete-btn { margin-top: 8px; }
        .request-form {
            display: grid;
            gap: 10px;
            text-align: left;
        }
        .request-form input,
        .request-form textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
        }
        .request-form textarea {
            min-height: 120px;
            resize: vertical;
        }
        .request-status {
            margin-top: 8px;
            font-size: 13px;
            color: #333;
        }
    `;
    document.head.appendChild(style);
}

function choosePostingIdentity() {
    addRuntimeStyles();

    return new Promise((resolve) => {
        const overlay = document.createElement("div");
        overlay.className = "identity-modal-overlay";

        const box = document.createElement("div");
        box.className = "identity-modal-box";
        box.innerHTML = `
            <h3>Choose how to post</h3>
            <p>Do you want to show your NSU ID or stay anonymous?</p>
            <div class="identity-modal-actions">
                <button class="identity-choice-btn show-id">Show ID</button>
                <button class="identity-choice-btn anonymous">Anonymous</button>
                <button class="identity-choice-btn cancel">Cancel</button>
            </div>
        `;

        overlay.appendChild(box);
        document.body.appendChild(overlay);

        box.querySelector(".show-id").addEventListener("click", () => {
            overlay.remove();
            resolve("id");
        });
        box.querySelector(".anonymous").addEventListener("click", () => {
            overlay.remove();
            resolve("anonymous");
        });
        box.querySelector(".cancel").addEventListener("click", () => {
            overlay.remove();
            resolve(null);
        });
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) {
                overlay.remove();
                resolve(null);
            }
        });
    });
}

function createTutorReviewElement(review) {
    const reviewDiv = document.createElement("div");
    reviewDiv.className = "review";
    reviewDiv.dataset.reviewId = review.id;
    reviewDiv.innerHTML = `
        <div>"${review.review_text}"</div>
        <div class="review-meta">${review.author_display || "Anonymous"}</div>
    `;

    if (review.author_email && review.author_email === currentUserEmail) {
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "delete-reply-btn review-delete-btn";
        deleteBtn.textContent = "Delete";
        deleteBtn.addEventListener("click", async () => {
            try {
                const response = await fetch(`/api/tutors/reviews/${review.id}`, { method: "DELETE" });
                const result = await response.json();
                if (!response.ok) {
                    alert(result.error || "Failed to delete review.");
                    return;
                }
                reviewDiv.remove();
            } catch (error) {
                console.error("Delete tutor review error:", error);
                alert("An error occurred while deleting the review.");
            }
        });
        reviewDiv.appendChild(deleteBtn);
    }

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
    if (ratingSpan) ratingSpan.textContent = `⭐ ${average.toFixed(1)}`;
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
            const tutorName = card.querySelector(".tutor-name")?.textContent.trim();
            const existingReviews = card.querySelector(".existing-reviews");
            if (!tutorName || !existingReviews) return;
            const reviewList = result[tutorName] || [];
            existingReviews.innerHTML = "";
            reviewList.forEach(review => existingReviews.appendChild(createTutorReviewElement(review)));
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
            const tutorName = card.querySelector(".tutor-name")?.textContent.trim();
            const ratingInfo = result[tutorName];
            if (ratingInfo) updateRatingText(card, ratingInfo.average);
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
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ tutor_name: tutorName, slot: slot })
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

function openTutorRequestModal() {
    addRuntimeStyles();
    const overlay = document.createElement("div");
    overlay.className = "identity-modal-overlay";
    const box = document.createElement("div");
    box.className = "identity-modal-box";
    box.innerHTML = `
        <h3>Request to Become a Tutor</h3>
        <form class="request-form">
            <input type="text" name="name" placeholder="Full Name" required>
            <input type="email" name="email" placeholder="NSU Email" required>
            <input type="text" name="major" placeholder="Major" required>
            <input type="text" name="year" placeholder="Year (Freshman, Sophomore, etc.)" required>
            <input type="text" name="subjects" placeholder="Subjects You Can Tutor" required>
            <input type="text" name="phone" placeholder="Phone Number (optional)">
            <textarea name="experience" placeholder="Experience, coursework, tutoring history, or other details..." required></textarea>
            <textarea name="availability" placeholder="Availability (days/times)" required></textarea>
            <label style="display:block; text-align:left; margin-top:8px;"><strong>Upload your resume here:</strong></label>
            <input type="file" name="resume" accept=".pdf,.doc,.docx">
            <div class="identity-modal-actions">
                <button type="submit" class="identity-choice-btn show-id">Submit</button>
                <button type="button" class="identity-choice-btn cancel request-cancel-btn">Cancel</button>
            </div>
            <div class="request-status"></div>
        </form>
    `;
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    const form = box.querySelector(".request-form");
    const status = box.querySelector(".request-status");
    if (currentUserEmail) {
        form.querySelector('input[name="email"]').value = currentUserEmail;
        form.querySelector('input[name="name"]').value = currentUserEmail.split("@")[0];
    }

    box.querySelector(".request-cancel-btn").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", (e) => { if (e.target === overlay) overlay.remove(); });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        status.textContent = "Submitting...";
        const formData = new FormData(form);
        try {
            const response = await fetch("/api/tutors/request", { method: "POST", body: formData });
            const result = await response.json();
            if (!response.ok) {
                status.textContent = result.error || "Failed to submit request.";
                return;
            }
            status.textContent = result.message || "Tutor request submitted.";
            setTimeout(() => overlay.remove(), 900);
        } catch (error) {
            console.error("Tutor request error:", error);
            status.textContent = "An error occurred while submitting the request.";
        }
    });
}

document.querySelectorAll(".review-toggle").forEach(button => {
    button.addEventListener("click", () => {
        const reviewBox = button.closest(".tutor-card")?.querySelector(".review-box");
        if (!reviewBox) return;
        reviewBox.classList.toggle("hidden");
        button.textContent = reviewBox.classList.contains("hidden") ? "View Reviews" : "Hide Reviews";
    });
});

document.querySelectorAll(".tutor-card").forEach(card => {
    const tutorName = card.querySelector(".tutor-name")?.textContent.trim();
    const stars = card.querySelectorAll(".star");
    const submitRatingBtn = card.querySelector(".submit-rating");
    const bookBtn = card.querySelector(".book-btn");
    let currentRating = 0;

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
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ tutor_name: tutorName, rating: ratingValue })
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
        const visibilityChoice = await choosePostingIdentity();
        if (!visibilityChoice) return;

        try {
            const response = await fetch("/api/tutors/reviews", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    tutor_name: tutorName,
                    review_text: reviewText,
                    visibility_choice: visibilityChoice
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

const becomeTutorBtn = document.querySelector(".become-tutor-btn");
if (becomeTutorBtn) becomeTutorBtn.addEventListener("click", openTutorRequestModal);

loadTutorReviews();
loadTutorRatings();

const requestedTutor = getQueryParam("tutor");
if (requestedTutor) {
    const matchingCard = Array.from(document.querySelectorAll(".tutor-card")).find(card => {
        const name = card.querySelector(".tutor-name")?.textContent.trim();
        return name === requestedTutor;
    });
    if (matchingCard) {
        const reviewBox = matchingCard.querySelector(".review-box");
        const toggleBtn = matchingCard.querySelector(".review-toggle");
        if (reviewBox && reviewBox.classList.contains("hidden")) {
            reviewBox.classList.remove("hidden");
            if (toggleBtn) toggleBtn.textContent = "Hide Reviews";
        }
        matchingCard.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}
</script>
"""



# --------------------------------------------------
# HTML INJECTION HELPERS
# --------------------------------------------------
def serve_home_with_runtime_script():
    file_path = os.path.join(UI_DIR, "home.html")
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    if re.search(r"</body>", html, flags=re.IGNORECASE):
        html = re.sub(r"</body>", HOME_RUNTIME_SCRIPT + "\n</body>", html, count=1, flags=re.IGNORECASE)
    else:
        html += HOME_RUNTIME_SCRIPT
    return Response(html, mimetype="text/html")


def serve_discussions_with_runtime_script():
    file_path = os.path.join(UI_DIR, "discussions.html")
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    current_user_email_json = json.dumps(session.get("user", ""))
    injected_script = DISCUSSIONS_RUNTIME_SCRIPT.replace("{{CURRENT_USER_EMAIL_JSON}}", current_user_email_json)
    html = re.sub(r"<script>[\s\S]*?</script>\s*</body>", injected_script + "\n</body>", html, count=1, flags=re.IGNORECASE)
    return Response(html, mimetype="text/html")


def serve_tutors_with_runtime_script():
    file_path = os.path.join(UI_DIR, "tutors.html")
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()
    current_user_email_json = json.dumps(session.get("user", ""))
    injected_script = TUTORS_RUNTIME_SCRIPT.replace("{{CURRENT_USER_EMAIL_JSON}}", current_user_email_json)
    html = re.sub(r"<script>[\s\S]*?</script>\s*</body>", injected_script + "\n</body>", html, count=1, flags=re.IGNORECASE)
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
    return serve_home_with_runtime_script()


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
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO students (email) VALUES (?)", (email,))
    conn.commit()
    conn.close()
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
        "SELECT * FROM discussions WHERE major = ? ORDER BY created_at DESC", (major,)
    ).fetchall()

    result = []
    for row in rows:
        d = dict(row)
        # compute fins_up from likes table
        like_count = conn.execute(
            "SELECT COUNT(*) FROM discussion_likes WHERE discussion_id = ?", (d["id"],)
        ).fetchone()[0]
        d["fins_up"] = like_count

        replies = conn.execute(
            "SELECT * FROM replies WHERE discussion_id = ? ORDER BY created_at ASC", (d["id"],)
        ).fetchall()
        reply_list = []
        for r in replies:
            rd = dict(r)
            rd["fins_up"] = conn.execute(
                "SELECT COUNT(*) FROM reply_likes WHERE reply_id = ?", (rd["id"],)
            ).fetchone()[0]
            reply_list.append(rd)

        d["replies"] = reply_list
        d["time"] = d["created_at"]
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

    user_email = session["user"]
    visibility_choice = str(data.get("visibility_choice", "anonymous")).strip().lower()
    identity = build_display_identity(user_email, visibility_choice)

    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO students (email) VALUES (?)", (user_email,))
    cur = conn.execute(
        """INSERT INTO discussions (major, title, author_email, author_display, post_visibility, fins_up)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (data["major"], data["question"], user_email, identity["author_display"], identity["post_visibility"])
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({
        "id": new_id,
        "major": data["major"],
        "title": data["question"],
        "time": "Just now",
        "author_email": user_email,
        "author_display": identity["author_display"],
        "post_visibility": identity["post_visibility"],
        "liked_by": [],
        "fins_up": 0,
        "replies": []
    }), 201


@app.route("/api/discussions/toggle_like", methods=["POST"])
def toggle_discussion_like():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or not data.get("discussion_id"):
        return jsonify({"error": "discussion_id is required"}), 400

    discussion_id = data["discussion_id"]
    user_email = session["user"]

    conn = get_db()
    existing = conn.execute(
        "SELECT 1 FROM discussion_likes WHERE discussion_id = ? AND student_email = ?",
        (discussion_id, user_email)
    ).fetchone()

    if existing:
        conn.execute(
            "DELETE FROM discussion_likes WHERE discussion_id = ? AND student_email = ?",
            (discussion_id, user_email)
        )
        liked = False
    else:
        conn.execute(
            "INSERT INTO discussion_likes (discussion_id, student_email) VALUES (?, ?)",
            (discussion_id, user_email)
        )
        liked = True

    conn.commit()
    fins_up = conn.execute(
        "SELECT COUNT(*) FROM discussion_likes WHERE discussion_id = ?", (discussion_id,)
    ).fetchone()[0]
    conn.execute("UPDATE discussions SET fins_up = ? WHERE id = ?", (fins_up, discussion_id))
    conn.commit()
    conn.close()

    return jsonify({"id": discussion_id, "fins_up": fins_up, "liked": liked}), 200


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

    # cascade: delete reply likes, replies, discussion likes, discussion
    reply_ids = [r["id"] for r in conn.execute(
        "SELECT id FROM replies WHERE discussion_id = ?", (discussion_id,)
    ).fetchall()]
    for rid in reply_ids:
        conn.execute("DELETE FROM reply_likes WHERE reply_id = ?", (rid,))
    conn.execute("DELETE FROM replies WHERE discussion_id = ?", (discussion_id,))
    conn.execute("DELETE FROM discussion_likes WHERE discussion_id = ?", (discussion_id,))
    conn.execute("DELETE FROM discussions WHERE id = ?", (discussion_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 200


# --------------------------------------------------
# REPLY ROUTES
# --------------------------------------------------
@app.route("/api/replies", methods=["POST"])
def create_reply():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or not data.get("discussion_id") or not data.get("reply_text"):
        return jsonify({"error": "Missing data"}), 400

    user_email = session["user"]
    visibility_choice = str(data.get("visibility_choice", "anonymous")).strip().lower()
    identity = build_display_identity(user_email, visibility_choice)

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO replies (discussion_id, reply_text, author_email, author_display, post_visibility, fins_up)
           VALUES (?, ?, ?, ?, ?, 0)""",
        (data["discussion_id"], data["reply_text"], user_email, identity["author_display"], identity["post_visibility"])
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({
        "id": new_id,
        "reply_text": data["reply_text"],
        "author_email": user_email,
        "author_display": identity["author_display"],
        "post_visibility": identity["post_visibility"],
        "liked_by": [],
        "fins_up": 0
    }), 201


@app.route("/api/replies/toggle_like", methods=["POST"])
def toggle_reply_like():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or not data.get("reply_id"):
        return jsonify({"error": "reply_id is required"}), 400

    reply_id = data["reply_id"]
    user_email = session["user"]

    conn = get_db()
    existing = conn.execute(
        "SELECT 1 FROM reply_likes WHERE reply_id = ? AND student_email = ?",
        (reply_id, user_email)
    ).fetchone()

    if existing:
        conn.execute(
            "DELETE FROM reply_likes WHERE reply_id = ? AND student_email = ?",
            (reply_id, user_email)
        )
        liked = False
    else:
        conn.execute(
            "INSERT INTO reply_likes (reply_id, student_email) VALUES (?, ?)",
            (reply_id, user_email)
        )
        liked = True

    conn.commit()
    fins_up = conn.execute(
        "SELECT COUNT(*) FROM reply_likes WHERE reply_id = ?", (reply_id,)
    ).fetchone()[0]
    conn.execute("UPDATE replies SET fins_up = ? WHERE id = ?", (fins_up, reply_id))
    conn.commit()
    conn.close()

    return jsonify({"id": reply_id, "fins_up": fins_up, "liked": liked}), 200


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

    conn.execute("DELETE FROM reply_likes WHERE reply_id = ?", (reply_id,))
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

    conn = get_db()
    rows = conn.execute(
        """SELECT tr.*, t.name as tutor_name
           FROM tutor_reviews tr
           JOIN tutors t ON tr.tutor_id = t.id
           ORDER BY tr.created_at ASC"""
    ).fetchall()
    conn.close()

    # rebuild grouped-by-name response to match frontend expectation
    result = {}
    for row in rows:
        name = row["tutor_name"]
        if name not in result:
            result[name] = []
        result[name].append({
            "id": row["id"],
            "review_text": row["review_text"],
            "author_email": row["author_email"],
            "author_display": row["author_display"],
            "post_visibility": row["post_visibility"],
            "time": row["created_at"]
        })

    return jsonify(result), 200


@app.route("/api/tutors/reviews", methods=["POST"])
def create_tutor_review():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json()
    if not data or not data.get("tutor_name") or not data.get("review_text"):
        return jsonify({"error": "Missing data"}), 400

    tutor_name = data["tutor_name"].strip()
    review_text = data["review_text"].strip()
    if not tutor_name or not review_text:
        return jsonify({"error": "Missing data"}), 400

    user_email = session["user"]
    visibility_choice = str(data.get("visibility_choice", "anonymous")).strip().lower()
    identity = build_display_identity(user_email, visibility_choice)

    conn = get_db()
    tutor = conn.execute("SELECT id FROM tutors WHERE name = ?", (tutor_name,)).fetchone()
    if not tutor:
        conn.close()
        return jsonify({"error": "Tutor not found"}), 404

    cur = conn.execute(
        """INSERT INTO tutor_reviews (tutor_id, author_email, author_display, post_visibility, review_text)
           VALUES (?, ?, ?, ?, ?)""",
        (tutor["id"], user_email, identity["author_display"], identity["post_visibility"], review_text)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()

    return jsonify({
        "id": new_id,
        "review_text": review_text,
        "author_email": user_email,
        "author_display": identity["author_display"],
        "post_visibility": identity["post_visibility"],
        "time": "Just now"
    }), 201


@app.route("/api/tutors/reviews/<int:review_id>", methods=["DELETE"])
def delete_tutor_review(review_id):
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_email = session["user"]

    conn = get_db()
    row = conn.execute("SELECT * FROM tutor_reviews WHERE id = ?", (review_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Review not found"}), 404
    if row["author_email"] != user_email:
        conn.close()
        return jsonify({"error": "You can only delete your own review"}), 403

    conn.execute("DELETE FROM tutor_reviews WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True}), 200


# --------------------------------------------------
# TUTOR RATING ROUTES
# --------------------------------------------------
@app.route("/api/tutors/ratings", methods=["GET"])
def get_tutor_ratings():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db()
    rows = conn.execute(
        """SELECT t.name, AVG(tr.rating) as average, COUNT(tr.id) as count
           FROM tutors t
           LEFT JOIN tutor_ratings tr ON t.id = tr.tutor_id
           GROUP BY t.id, t.name"""
    ).fetchall()
    conn.close()

    result = {}
    for row in rows:
        result[row["name"]] = {
            "average": round(row["average"] or 0, 1),
            "count": row["count"] or 0
        }
    return jsonify(result), 200


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

    conn = get_db()
    tutor = conn.execute("SELECT id FROM tutors WHERE name = ?", (tutor_name,)).fetchone()
    if not tutor:
        conn.close()
        return jsonify({"error": "Tutor not found"}), 404

    # upsert — one rating per user per tutor
    conn.execute(
        """INSERT INTO tutor_ratings (tutor_id, student_email, rating)
           VALUES (?, ?, ?)
           ON CONFLICT(tutor_id, student_email) DO UPDATE SET rating = excluded.rating""",
        (tutor["id"], user_email, rating_value)
    )
    conn.commit()

    row = conn.execute(
        "SELECT AVG(rating) as average, COUNT(*) as count FROM tutor_ratings WHERE tutor_id = ?",
        (tutor["id"],)
    ).fetchone()
    conn.close()

    return jsonify({
        "tutor_name": tutor_name,
        "average": round(row["average"] or 0, 1),
        "count": row["count"],
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

    conn = get_db()
    tutor = conn.execute("SELECT id FROM tutors WHERE name = ?", (tutor_name,)).fetchone()
    if not tutor:
        conn.close()
        return jsonify({"tutor_name": tutor_name, "available_slots": []}), 200

    rows = conn.execute(
        "SELECT slot_text FROM tutor_availability WHERE tutor_id = ? AND is_booked = 0",
        (tutor["id"],)
    ).fetchall()
    conn.close()

    return jsonify({
        "tutor_name": tutor_name,
        "available_slots": [r["slot_text"] for r in rows]
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

    conn = get_db()
    tutor = conn.execute("SELECT id FROM tutors WHERE name = ?", (tutor_name,)).fetchone()
    if not tutor:
        conn.close()
        return jsonify({"error": "Tutor not found"}), 404

    slot_row = conn.execute(
        "SELECT id, is_booked FROM tutor_availability WHERE tutor_id = ? AND slot_text = ?",
        (tutor["id"], slot)
    ).fetchone()

    if not slot_row:
        conn.close()
        return jsonify({"error": "That slot does not exist"}), 404
    if slot_row["is_booked"]:
        conn.close()
        return jsonify({"error": "That time is no longer available"}), 400

    # mark slot booked and record booking
    conn.execute("UPDATE tutor_availability SET is_booked = 1 WHERE id = ?", (slot_row["id"],))
    conn.execute(
        "INSERT INTO tutor_bookings (tutor_id, student_email, slot_text) VALUES (?, ?, ?)",
        (tutor["id"], user_email, slot)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "message": "Session booked successfully",
        "tutor_name": tutor_name,
        "slot": slot
    }), 201


@app.route("/api/tutors/request", methods=["POST"])
def create_tutor_request():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    form = request.form
    name         = form.get("name", "").strip()
    email        = form.get("email", "").strip().lower()
    major        = form.get("major", "").strip()
    year         = form.get("year", "").strip()
    subjects     = form.get("subjects", "").strip()
    phone        = form.get("phone", "").strip()
    experience   = form.get("experience", "").strip()
    availability = form.get("availability", "").strip()

    if not name or not email or not major or not year or not subjects or not experience or not availability:
        return jsonify({"error": "Name, email, major, year, subjects, experience, and availability are required"}), 400
    if not email.endswith("@mynsu.nova.edu"):
        return jsonify({"error": "Only NSU student emails allowed"}), 400

    resume = request.files.get("resume")
    saved_resume_path = ""
    saved_resume_name = ""

    if resume and resume.filename:
        saved_resume_name = secure_filename(resume.filename)
        saved_resume_path = os.path.join(UPLOAD_DIR, saved_resume_name)
        counter = 1
        root, ext = os.path.splitext(saved_resume_name)
        while os.path.exists(saved_resume_path):
            saved_resume_name = f"{root}_{counter}{ext}"
            saved_resume_path = os.path.join(UPLOAD_DIR, saved_resume_name)
            counter += 1
        resume.save(saved_resume_path)

    conn = get_db()
    conn.execute(
        """INSERT INTO tutor_requests
           (name, email, major, year, subjects, phone, experience, availability, resume_filename, submitted_by)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, email, major, year, subjects, phone, experience, availability, saved_resume_name, session["user"])
    )
    conn.commit()
    conn.close()

    request_record = {
        "name": name, "email": email, "major": major, "year": year,
        "subjects": subjects, "phone": phone, "experience": experience, "availability": availability
    }

    sent, message = send_tutor_request_email(
        request_record,
        saved_resume_path if saved_resume_path else None
    )

    return jsonify({
        "success": True,
        "email_sent": sent,
        "message": "Tutor request submitted successfully." if sent else message
    }), 201


# --------------------------------------------------
# START SERVER
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
