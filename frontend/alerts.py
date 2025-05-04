import streamlit as st
import sqlite3
import os
from datetime import datetime

# ─── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(__file__))   # project root
DB_PATH  = os.path.join(BASE_DIR, "data", "app_database.db")  # Database path

# --- Helper: fetch from user_posts ---
def fetch_user_posts(user_email: str):
    """
    Return all rows for this user as a list of dicts, including the post ID.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, timestamp, post_content, image_name, sentiment, confidence
          FROM user_posts
         WHERE username = ?
         ORDER BY timestamp DESC
    """, (user_email,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "id":          row[0],
            "timestamp":   row[1],
            "content":     row[2],
            "image":       row[3],
            "sentiment":   row[4],
            "confidence":  row[5]
        }
        for row in rows
    ]

# --- Alerts & Flagged Posts Page ---
def app():
    st.title("🚨 **Alerts & Flagged Posts**")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Ensure user is logged in
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("❌ You must log in (enter your email) before viewing the alerts.")
        return
    user_email = str(user_email)

    # Fetch all posts for the logged-in user
    user_stats = fetch_user_posts(user_email)

    # Pull reviewed post_ids from alerts table
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT post_id
          FROM alerts
         WHERE post_id IN (
             SELECT id FROM user_posts WHERE username = ?
         )
    """, (user_email,))
    reviewed_ids = {row[0] for row in cur.fetchall()}
    conn.close()

    # Filter for unreviewed negative posts
    negative = [
        p for p in user_stats
        if p["sentiment"] == "negative" and p["id"] not in reviewed_ids
    ]

    # --- Display Unreviewed Negative Posts ---
    st.subheader("⚠️ **Flagged Posts Awaiting Admin Review**")
    if negative:
        st.error(f"⚠️ You have **{len(negative)}** flagged post(s) awaiting review.")
        with st.expander("🔍 View Flagged Posts"):
            for p in negative:
                try:
                    ts = datetime.fromisoformat(p["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    ts = p["timestamp"]
                text = p["content"] or "🖼️ Image post"
                conf = p["confidence"] or 0.0
                st.markdown(f"🔴 **{ts}** — {text} (Confidence: {conf:.2f})")
    else:
        st.success("✅ No flagged posts. Great job!")

    # Fetch admin-reviewed posts with feedback
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            up.id AS post_id,
            up.timestamp AS flagged_at,
            up.post_content,
            up.image_name,
            up.sentiment,
            up.confidence,
            a.admin_username,
            a.comment AS admin_comment,
            a.timestamp AS reviewed_on
        FROM user_posts AS up
        JOIN alerts   AS a  ON up.id = a.post_id
       WHERE up.username = ?
       ORDER BY a.timestamp DESC
    """, (user_email,))
    reviewed = cur.fetchall()
    conn.close()

    # --- Display Reviewed Flagged Posts with Admin Feedback ---
    st.subheader("📝 **Reviewed Flagged Posts with Admin Feedback**")
    if reviewed:
        # New count line with smiley
        st.success(f"😊 You have **{len(reviewed)}** reviewed post(s) with admin feedback.")
        for (
            post_id, flagged_at, content, image_name,
            sentiment, confidence, admin_user, admin_comment, reviewed_on
        ) in reviewed:
            # Format timestamps
            try:
                ts_flagged = datetime.fromisoformat(flagged_at).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts_flagged = flagged_at
            try:
                ts_reviewed = datetime.fromisoformat(reviewed_on).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                ts_reviewed = reviewed_on

            # Color code sentiment
            sentiment_color = "green" if sentiment == "positive" else "red"

            # Random encouragement
            encouragement_options = [
                "🌟 Strive for positive posts. Your confidence is growing!",
                "👍 Spread positivity! You are amazing.",
                "💪 You’re on the right track! Every post counts towards a better community.",
                "✨ Keep it up! Positive vibes."
            ]
            encouragement = encouragement_options[hash(content) % len(encouragement_options)]
            box_class = "info-posts" if sentiment == "positive" else "alert-posts"

            with st.expander(f"Reviewed on {ts_reviewed}"):
                st.markdown(
                    f"<div class='{box_class}' style='padding:15px; margin-bottom:20px;'>"
                    f"<p style='color:{sentiment_color};"
                    f" font-size:18px; font-weight:bold;'>"
                    f"🟢 {ts_flagged} — {content}"
                    f" (Reviewed on {ts_reviewed})</p>"
                    , unsafe_allow_html=True
                )
                st.write(f"📝 **Admin Comment**: {admin_comment}")
                st.write(f"💬 **Encouragement**: {encouragement}")
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("ℹ️ You have no flagged posts reviewed by admin. Keep posting with confidence!")

    # --- Footer Styling ---
    st.markdown(
        """
        <style>
        .footer {
            position: fixed;
            bottom: 10px;
            left: 10px;
            color: gray;
            font-size: 12px;
        }
        .alert-posts {
            background-color: #FFEBEE;
            border-left: 4px solid #F44336;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .info-posts {
            background-color: #E8F5E9;
            border-left: 4px solid #4CAF50;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        </style>
        <div class="footer">
            © 2025 Social Media Sentiment Health Analysis
        </div>
        """,
        unsafe_allow_html=True
    )
