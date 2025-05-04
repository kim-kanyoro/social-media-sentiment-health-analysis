import random
import sqlite3
import os
import streamlit as st
from datetime import datetime
from textblob import TextBlob

# =========================
# Configurations
# =========================
DB_PATH = os.path.join("data", "app_database.db")
UPLOAD_DIR = os.path.join("data", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# =========================
# Emoji Map
# =========================
EMOJI_MAP = {
    "positive": "😄🎉",
    "negative": "😔⚠️",
    "neutral":  "😐"
}

# =========================
# Database Initialization
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            post_content TEXT,
            image_name TEXT,
            sentiment TEXT,
            confidence REAL,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

# =========================
# Sentiment Analysis (Real)
# =========================
def analyze_sentiment(text: str) -> dict:
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # range: -1 to 1

    if polarity > 0.1:
        sentiment = "positive"
    elif polarity < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    confidence = round(abs(polarity), 2)
    return {"sentiment": sentiment, "confidence": confidence}

# =========================
# Image Analysis (Fake)
# =========================
def analyze_image_sentiment(image) -> tuple:
    choices = ["positive", "negative", "neutral"]
    sentiment = random.choice(choices)
    confidence = random.uniform(0.5, 1.0)
    return sentiment, confidence

# =========================
# Core Database Operations
# =========================
def save_user_post(user_email: str, text: str = None, image=None, sentiment: str = None, confidence: float = None) -> bool:
    try:
        img_name = None
        if image:
            img_name = image.name
            img_path = os.path.join(UPLOAD_DIR, img_name)
            with open(img_path, "wb") as f:
                f.write(image.getbuffer())

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_posts (username, post_content, image_name, sentiment, confidence, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (user_email, text or "", img_name, sentiment, confidence, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

        if sentiment == "negative":
            st.error("⚠️ Admin has been notified of the negative sentiment!")
        return True
    except Exception as e:
        st.error(f"Error saving post: {e}")
        return False

def get_user_posts(user_email: str) -> list:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, post_content, image_name, sentiment, confidence FROM user_posts WHERE username = ? ORDER BY timestamp DESC",
            (user_email,)
        )
        records = cursor.fetchall()
        conn.close()
        return [
            {"timestamp": ts, "content": txt, "image": img, "sentiment": s, "confidence": c}
            for ts, txt, img, s, c in records
        ]
    except Exception as e:
        st.error(f"Error fetching posts: {e}")
        return []

# =========================
# Streamlit App Page
# =========================
def app():
    init_db()
    st.title("📊 Sentiment Analysis Report")

    # Simulated login (hardcoded for demo)
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = st.text_input("Enter your email to continue:")
        if not st.session_state["user_email"]:
            st.stop()

    user_email = st.session_state["user_email"]

    st.subheader("📝 Analyze a New Post")
    input_type = st.radio("Choose input type:", ["Text", "Image"])

    sentiment, confidence = None, None
    if input_type == "Text":
        user_text = st.text_area("Enter your post here...")
        if st.button("Analyze Text"):
            if user_text.strip():
                result = analyze_sentiment(user_text)
                sentiment, confidence = result["sentiment"], result["confidence"]
                save_user_post(user_email, text=user_text, sentiment=sentiment, confidence=confidence)
            else:
                st.warning("Please enter some text before analyzing.")
    else:
        uploaded_file = st.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])
        if st.button("Analyze Image"):
            if uploaded_file:
                sentiment, confidence = analyze_image_sentiment(uploaded_file)
                save_user_post(user_email, image=uploaded_file, sentiment=sentiment, confidence=confidence)
            else:
                st.warning("Please upload an image before analyzing.")

    if sentiment:
        st.success(f"**Sentiment:** {EMOJI_MAP.get(sentiment)} {sentiment.capitalize()}")
        if sentiment == "negative":
            st.error("⚠️ Wait for reveiw, Check on alerts for updates.")

    st.subheader(f"📜 Previous Analysis for: `{user_email}`")
    posts = get_user_posts(user_email)
    if not posts:
        st.info("No sentiment analysis data found.")
        return

    for idx, post in enumerate(posts):
        try:
            ts = datetime.fromisoformat(post['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
        except:
            ts = post['timestamp']
        emoji = EMOJI_MAP.get(post['sentiment'], '❓')
        exp_label = f"{ts} — {emoji} {post['sentiment'].capitalize()}"
        with st.expander(exp_label, expanded=False):
            if post['content']:
                st.write(f"**Text:** {post['content']}")
            if post['image']:
                img_path = os.path.join(UPLOAD_DIR, post['image'])
                if os.path.exists(img_path):
                    st.image(img_path, caption="Uploaded Image", use_column_width=True)
            st.write(f"**Confidence:** {post['confidence']:.2f}")

# =========================
# Run App
# =========================
if __name__ == "__main__":
    app()
