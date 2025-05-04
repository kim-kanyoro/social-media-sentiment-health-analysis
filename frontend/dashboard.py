import streamlit as st
import sqlite3
import os
import matplotlib.pyplot as plt
from datetime import datetime

# ─── Paths ─────────────────────────────────────────────────────────────────────
# Ensure we point at the same DB your main app created:
BASE_DIR = os.path.dirname(os.path.dirname(__file__))   # project root
DB_PATH  = os.path.join(BASE_DIR, "data", "app_database.db")


# ─── Helper: fetch from user_posts ─────────────────────────────────────────────
def fetch_user_posts(user_email: str):
    """Return all rows for this user as a list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT timestamp, post_content, image_name, sentiment, confidence
          FROM user_posts
         WHERE username = ?
         ORDER BY timestamp DESC
    """, (user_email,))
    rows = cur.fetchall()
    conn.close()

    return [
        {
            "timestamp":   ts,
            "content":     content,
            "image":       image_name,
            "sentiment":   sentiment,
            "confidence":  confidence
        }
        for ts, content, image_name, sentiment, confidence in rows
    ]


# ─── Streamlit Dashboard Page ─────────────────────────────────────────────────
def app():
    st.title("📊 Dashboard")

    # 1) Read the same key your main app uses:
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("You must log in (enter your email) before viewing the dashboard.")
        return
    user_email = str(user_email)

    # 2) Load all posts from the shared user_posts table
    user_stats = fetch_user_posts(user_email)

    # ─── Alerts & Notifications ────────────────────────────────────────────────
    st.subheader("🚨 Alerts & Notifications")
    negative = [p for p in user_stats if p["sentiment"] == "negative"]

    if negative:
        st.error(f"⚠️ You have {len(negative)} unreviewed flagged post(s)")
        with st.expander("View Unreviewed Posts"):
            for p in negative:
                # format timestamp cleanly
                try:
                    ts = datetime.fromisoformat(p["timestamp"])\
                                 .strftime("%Y-%m-%d %H:%M:%S")
                except:
                    ts = p["timestamp"]
                text = p["content"] or "🖼️ Image post"
                conf = p["confidence"] or 0.0
                st.write(f"- **{ts}** — {text} (Confidence: {conf:.2f})")
    else:
        st.success("✅ No Flagged posts. Great job!")


    # ─── Sentiment Analysis Overview ───────────────────────────────────────────
    st.subheader("📈 Sentiment Analysis Overview for You")
    if not user_stats:
        st.warning("You have no posts to analyze yet.")
        return

    # tally counts
    sentiments = ["positive", "negative", "neutral"]
    counts = {s: sum(1 for p in user_stats if p["sentiment"] == s)
              for s in sentiments}
    total = len(user_stats)

    # metric cards
    c1, c2, c3 = st.columns(3)
    c1.metric("Positive", counts["positive"])
    c2.metric("Negative", counts["negative"])
    c3.metric("Neutral",  counts["neutral"])

    # side-by-side charts
    chart1, chart2 = st.columns(2)

    with chart1:
        fig1, ax1 = plt.subplots()
        ax1.pie(
            [counts[s] for s in sentiments],
            labels=[s.capitalize() for s in sentiments],
            autopct="%1.1f%%",
            startangle=90
        )
        ax1.axis("equal")
        st.pyplot(fig1)

    with chart2:
        fig2, ax2 = plt.subplots()
        ax2.bar(
            [s.capitalize() for s in sentiments],
            [counts[s] for s in sentiments]
        )
        ax2.set_ylabel("Count")
        ax2.set_title("Sentiment Counts")
        st.pyplot(fig2)

    st.markdown(f"**🧾 Total Analyzed Posts:** {total}")


    # ─── Footer ────────────────────────────────────────────────────────────────
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
        </style>
        <div class="footer">
            © 2025 Social Media Sentiment Health Analysis
        </div>
        """,
        unsafe_allow_html=True
    )
