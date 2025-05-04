import streamlit as st
import pandas as pd
from backend import database
import os
import sqlite3
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import schedule
import threading
import time
from textblob import TextBlob

# --- Constants ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
USERS_PER_PAGE = 5

# Hardcoded SMTP credentials
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "kimanikanyoro4@gmail.com"        # <-- enter  your email
SMTP_PASS = "qenw vyus yhyr bpah"      # <-- enter your password

# --- Database setup ---
def create_alerts_table():
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "data", "app_database.db")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER UNIQUE,
            admin_username TEXT,
            comment TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES user_posts(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()

create_alerts_table()

# --- Dynamic comment generator ---
def generate_dynamic_comment(post_text: str) -> str:
    blob = TextBlob(post_text)
    sentences = blob.sentences
    if sentences:
        scored = [(s.sentiment.polarity, str(s)) for s in sentences]
        min_score, worst = min(scored, key=lambda x: x[0])
        if min_score <= -0.5:
            return (f"I noticed this part of your post was quite negative: \"{worst}\". "
                    "I understand this might come from frustration—would you consider reframing it with specific examples or a constructive solution? "
                    "This will help others understand your perspective and foster a more positive dialogue.")
        elif min_score <= -0.2:
            return (f"Your post segment \"{worst}\" carries a somewhat negative tone. "
                    "You might enhance it by adding supportive comments or actionable suggestions. "
                    "For instance, sharing a small positive outcome or an improvement idea can balance the message.")
        else:
            return ("Thanks for sharing your thoughts! To make your post even more engaging, "
                    "consider elaborating with examples or helpful resources. "
                    "This context will make your feedback more impactful for readers.")
    return ("Thanks for posting! If you’d like feedback, try adding more details or clarifying your main points. "
            "The more context you provide, the better we (and other readers) can understand your perspective.")

# --- Auto-review scheduler routine ---
def auto_process_flagged():
    """
    Find every negative post that hasn’t been reviewed yet,
    generate a dynamic comment, mark it reviewed, and email the user.
    """
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DB_PATH  = os.path.join(BASE_DIR, "data", "app_database.db")
    conn     = sqlite3.connect(DB_PATH)
    cur      = conn.cursor()

    # 1) get all new negatives
    cur.execute("""
        SELECT p.id, p.username, p.post_content, p.sentiment, p.confidence
          FROM user_posts p
     LEFT JOIN alerts a ON p.id = a.post_id
         WHERE p.sentiment = 'negative'
           AND a.post_id IS NULL
    """)
    posts = cur.fetchall()

    # get all users once
    users = {u['username']: u['email'] for u in database.get_all_users()}

    for post_id, user, text, senti, conf in posts:
        email = users.get(user)
        if not email:
            continue

        # 2) dynamic comment
        comment = generate_dynamic_comment(text)
        now     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 3) mark reviewed in DB
        try:
            cur.execute(
                "INSERT INTO alerts(post_id,admin_username,comment,timestamp) VALUES(?,?,?,?)",
                (post_id, "system", comment, now)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            continue

        # 4) send email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "[Action Required] Please Review Your Post"
        msg["From"]    = SMTP_USER
        msg["To"]      = email

        html = f"""
        <html><body style="font-family:Arial,sans-serif;padding:20px;">
          <h2 style="color:#4a90e2;">Your Post Needs Review</h2>
          <p>Hi <strong>{user}</strong>,</p>
          <p>We detected a negative tone (confidence {conf:.2f}) in your post:</p>
          <blockquote style="background:#eee;padding:10px;border-left:4px solid #4a90e2;">
            {text}
          </blockquote>
          <p><strong>Feedback:</strong><br>{comment}</p>
          <p><a href="https://your-app-url.com/posts/{post_id}/edit"
                style="color:#4a90e2;">Edit your post</a> and we’ll re-check.</p>
          <p style="font-size:12px;color:#555;">— Support Team</p>
        </body></html>
        """
        msg.attach(MIMEText(html, "html"))
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.sendmail(SMTP_USER, email, msg.as_string())
        except Exception as e:
            print(f"Email failed for post {post_id}: {e}")

    conn.close()

# --- Scheduler setup ---
def _scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    if not st.session_state.get("scheduler_running", False):
        schedule.every(3).minutes.do(auto_process_flagged)
        auto_process_flagged()  # run once on startup
        threading.Thread(target=_scheduler_loop, daemon=True).start()
        st.session_state["scheduler_running"] = True




# --- Page Sections ---
def show_dashboard():
    st.markdown("## 📝 Summary & Analytics Dashboard")
    users = database.get_all_users()
    total_users = len(users)

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "data", "app_database.db")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM user_posts WHERE sentiment='negative'")
    flagged_count = cur.fetchone()[0]
    cur.execute("SELECT sentiment, COUNT(*) FROM user_posts GROUP BY sentiment")
    sentiment_data = cur.fetchall()
    cur.execute("SELECT DATE(timestamp) AS date, COUNT(*) FROM user_posts GROUP BY DATE(timestamp)")
    timeseries_data = cur.fetchall()
    conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Users", total_users)
    col2.metric("Flagged Posts", flagged_count)
    avg_posts = sum(c for _, c in timeseries_data) / (len(timeseries_data) or 1)
    col3.metric("Avg Posts/Day", f"{avg_posts:.1f}")

    st.markdown("---")
    st.markdown("### Analytics Snapshots")
    left, right = st.columns(2)

    with left:
        st.markdown("**📊 Sentiment Distribution**")
        df_sent = pd.DataFrame(sentiment_data, columns=["Sentiment", "Count"]).set_index("Sentiment")
        fig1, ax1 = plt.subplots(figsize=(4.2, 2.6))
        ax1.pie(df_sent['Count'], labels=df_sent.index, autopct='%1.1f%%', startangle=140)
        ax1.axis('equal')
        st.pyplot(fig1)

    with right:
        st.markdown("**💡 Users Helped Over Time**")
        today = pd.to_datetime("today")
        dates_helped = pd.date_range(today - pd.Timedelta(days=10), today)
        helped_counts = np.cumsum(np.random.randint(0, 5, size=len(dates_helped)))
        df_helped = pd.DataFrame({'Date': dates_helped, 'UsersHelped': helped_counts}).set_index('Date')
        fig4, ax4 = plt.subplots(figsize=(4.2, 2.6))
        ax4.plot(df_helped.index, df_helped['UsersHelped'], marker='s')
        ax4.set_xlabel('Date')
        ax4.set_ylabel('Users Helped')
        ax4.set_title('Users Helped')
        ax4.tick_params(axis='x', rotation=45)
        st.pyplot(fig4)
        st.download_button("📥 Download Helped Users CSV",
                           df_helped.reset_index().to_csv(index=False),
                           "users_helped.csv", "text/csv")

    st.markdown("---")
    st.markdown("### Engagement Over Time")

    with st.expander("🔍 Filter Options"):
        days_range = st.slider("Select number of past days", min_value=5, max_value=30, value=10)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📈 Posts Over Time**")
        today = pd.to_datetime("today")
        dates = pd.date_range(today - pd.Timedelta(days=days_range), today)
        counts = np.random.poisson(lam=10, size=len(dates))
        df_time = pd.DataFrame({'Date': dates, 'Count': counts}).set_index('Date')
        fig2, ax2 = plt.subplots(figsize=(4.2, 2.5))
        ax2.plot(df_time.index, df_time['Count'], marker='o')
        ax2.set_xlabel('Date')
        ax2.set_ylabel('Posts')
        ax2.set_title('Posts Over Time')
        ax2.tick_params(axis='x', rotation=45)
        st.pyplot(fig2)
        st.download_button("📥 Download Posts CSV",
                           df_time.reset_index().to_csv(index=False),
                           "posts_over_time.csv", "text/csv")

    with col2:
        st.markdown("**👥 User Growth Over Time**")
        dates_users = pd.date_range(today - pd.Timedelta(days=days_range), today)
        user_counts = np.cumsum(np.random.randint(0, 3, size=len(dates_users)))
        df_users = pd.DataFrame({"SignupDate": dates_users, "TotalUsers": user_counts}).set_index('SignupDate')
        fig3, ax3 = plt.subplots(figsize=(4.2, 2.5))
        ax3.bar(df_users.index, df_users['TotalUsers'])
        ax3.set_xlabel('Date')
        ax3.set_ylabel('Users')
        ax3.set_title('User Growth')
        ax3.tick_params(axis='x', rotation=45)
        st.pyplot(fig3)
        st.download_button("📥 Download User Growth CSV",
                           df_users.reset_index().to_csv(index=False),
                           "user_growth.csv", "text/csv")


def show_users():
    st.markdown("### 👥 All Registered Users")
    # Initialize deleted users list
    if "deleted_users" not in st.session_state:
        st.session_state["deleted_users"] = []

    search_term = st.text_input("🔍 Search by username or email").lower()
    users = database.get_all_users()
    if not users:
        st.info("No users found.")
        return

    # Filter by search term
    filtered = [u for u in users if search_term in u["username"].lower() or search_term in u["email"].lower()]
    total = len(filtered)
    st.markdown(f"**Total Users Found: {total}**")

    # Pagination
    pages = (total - 1) // USERS_PER_PAGE + 1
    page = st.number_input("Page", 1, pages, 1)
    start = (page - 1) * USERS_PER_PAGE
    end = start + USERS_PER_PAGE

    for u in filtered[start:end]:
        uid = u['id']
        username = u['username']
        email = u['email']
        with st.expander(f"👤 {username} - {email}"):
            # Edit form: only email editable
            with st.form(key=f"edit_form_{uid}"):
                st.text_input("Username", value=username, disabled=True)
                new_email = st.text_input("Email", value=email)
                if st.form_submit_button("💾 Save Changes"):
                    if new_email != email:
                        database.update_user(uid, username, new_email)
                        st.success("✅ Email updated successfully.")
                        st.rerun()
                    else:
                        st.info("No changes detected.")

            # Delete flow
            if username != ADMIN_USERNAME:
                # Trigger confirmation state
                if st.button("🗑️ Delete", key=f"del_{uid}"):
                    st.session_state[f"confirm_delete_{uid}"] = True

                if st.session_state.get(f"confirm_delete_{uid}", False):
                    with st.form(key=f"delete_form_{uid}"):
                        st.warning(f"Are you sure you want to delete **{username}**?")
                        confirm = st.form_submit_button("✅ Confirm Delete")
                        cancel = st.form_submit_button("❌ Cancel")
                        if confirm:
                            # Record deleted user
                            from datetime import datetime
                            st.session_state["deleted_users"].append({
                                "id": uid,
                                "username": username,
                                "email": email,
                                "deleted_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            database.delete_user(uid)
                            st.success("✅ User deleted.")
                            st.session_state[f"confirm_delete_{uid}"] = False
                            st.rerun()
                        if cancel:
                            st.session_state[f"confirm_delete_{uid}"] = False
                            st.info("🛑 Deletion cancelled.")
            else:
                st.markdown("🚫 Cannot delete admin")

    # Table of recently deleted users
    if st.session_state["deleted_users"]:
        st.markdown("### 🗑️ Recently Deleted Users")
        df_del = pd.DataFrame(st.session_state["deleted_users"])
        st.table(df_del)



import os
import sqlite3
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import pandas as pd
import streamlit as st
from textblob import TextBlob

# Ensure SMTP_USER, SMTP_PASS, SMTP_SERVER, SMTP_PORT are defined in session state or config

def show_flagged():
    st.markdown("### 🚨 Flagged Content for Review")

    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "data", "app_database.db")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute('''
        SELECT id, username, timestamp, post_content, image_name, sentiment, confidence
        FROM user_posts
        WHERE sentiment = 'negative'
        ORDER BY timestamp DESC
    ''')
    flagged = cur.fetchall()

    cur.execute('SELECT post_id, admin_username, comment, timestamp FROM alerts')
    alerts = cur.fetchall()
    conn.close()

    alert_map = {
        post_id: {
            "admin": admin if admin else "admin",
            "comment": comment.strip() if comment else "",
            "timestamp": alert_time
        }
        for post_id, admin, comment, alert_time in alerts
    }

    if not flagged:
        st.info("No flagged content to review.")
        return

    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        hide_reviewed = st.checkbox("🙈 Hide Reviewed", value=False)
    with col2:
        sort_order = st.radio("🔃 Sort Order", ["Reviewed First", "Unreviewed First"], horizontal=True)
    with col3:
        auto_review_all = st.button("🤖 Auto Review All")

    reviewed_posts = [f for f in flagged if f[0] in alert_map]
    unreviewed_posts = [f for f in flagged if f[0] not in alert_map]
    total_reviewed = len(reviewed_posts)
    total_pending = len(unreviewed_posts)
    st.markdown(f"🟢 Reviewed: **{total_reviewed}** | 🕒 Pending: **{total_pending}**")

    ordered = reviewed_posts + unreviewed_posts if sort_order == "Reviewed First" else unreviewed_posts + reviewed_posts

    def send_email(to_addr: str, subject: str, html_body: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to_addr
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_addr, msg.as_string())

    def build_email_template(title: str, recipient: str, body_html: str) -> str:
        return f"""
        <html>
          <body style="font-family: 'Helvetica Neue',Arial,sans-serif; background-color:#fef9f0; color:#333; padding:20px;">
            <div style="max-width:600px; margin:auto; background:#ffffff; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
              <div style="background:#ffcc80; border-top-left-radius:8px; border-top-right-radius:8px; padding:20px; text-align:center;">
                <h1 style="margin:0; color:#5d4037;">{title}</h1>
              </div>
              <div style="padding:20px;">
                <p style="font-size:16px; line-height:1.5;">Dear {recipient},</p>
                {body_html}
              </div>
            </div>
          </body>
        </html>
        """

    def auto_review(post_id, username, content, recipient=None):
        # Generate dynamic, descriptive comment
        blob = TextBlob(content)
        polarity, subjectivity = blob.sentiment
        tone = "positive" if polarity > 0 else "negative" if polarity < 0 else "neutral"
        comment = (
            f"Your post appears {tone} (polarity={polarity:.2f}, subjectivity={subjectivity:.2f}). "
            f"Please reflect on the tone and consider rephrasing if needed.<br/><br/>"
            f"<em>Extracted content insight:</em> \"{content}\""
        )
        admin_username = st.session_state.get("username", "auto")
        timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Save alert
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            '''
            INSERT INTO alerts (post_id, admin_username, comment, timestamp)
            VALUES (?, ?, ?, ?)
            ''', (post_id, admin_username, comment, timestamp_now)
        )
        conn.commit()
        conn.close()

        default_email = username if "@" in username else f"{username}@gmail.com"
        email_to = recipient or st.text_input(
            "Confirm recipient email:", value=default_email, key=f"email_confirm_{post_id}"
        )
        if st.button(f"📧 Confirm & Send Auto-Review (ID {post_id})", key=f"send_auto_{post_id}"):
            try:
                html_body = build_email_template(
                    title="Automatic Review Completed",
                    recipient=username,
                    body_html=f"""
                        <p style=\"font-size:16px; line-height:1.5;\">Your flagged post has been reviewed automatically. Please see the comment below:</p>
                        <blockquote style=\"background:#fff3e0; border-left:4px solid #ffb74d; margin:20px 0; padding:15px; border-radius:4px; font-style:italic; color:#795548;\">{comment}</blockquote>
                        <p style=\"font-size:16px; line-height:1.5;\">If you have any concerns, reply to this message.</p>
                    """
                )
                send_email(email_to, "Auto Review Notification", html_body)
                st.success(f"✅ Auto reviewed and emailed {email_to}")
            except Exception as e:
                st.error(f"❌ Failed to auto email {email_to}: {e}")

    if auto_review_all:
        for post_id, username, timestamp, content, *_ in unreviewed_posts:
            auto_review(post_id, username, content or "Image Post")
        st.success(f"✅ All {total_pending} posts auto-reviewed and emailed.")
        st.rerun()

    reviewed_data = []
    for post_id, username, timestamp, content, image_name, sentiment, confidence in ordered:
        if hide_reviewed and post_id in alert_map:
            continue

        reviewed = post_id in alert_map
        icon = "✅" if reviewed else "⚠️"
        post_text = content or "🖼️ Image post"
        box_color = "#e7f4ea" if reviewed else "#fdecea"

        with st.expander(f"{icon} {timestamp} | {username}"):
            st.markdown(
                f"""
                <div style="background-color: {box_color}; padding: 10px; border-radius: 5px;">
                    <strong>Sentiment:</strong> {sentiment.capitalize()}<br>
                    <strong>Confidence:</strong> {confidence:.2f}<br>
                    <strong>Post:</strong> {post_text}
                </div>
                """, unsafe_allow_html=True
            )

            if reviewed:
                alert = alert_map[post_id]
                st.markdown(f"**💬 Admin Comment ({alert['timestamp']} by {alert['admin']}):** {alert['comment']}")

                # Edit comment
                if st.button("✏️ Edit Comment", key=f"edit_btn_{post_id}"):
                    st.session_state[f"edit_mode_{post_id}"] = True
                if st.session_state.get(f"edit_mode_{post_id}"):
                    new_comment = st.text_area("Edit Comment", value=alert['comment'], key=f"edit_txt_{post_id}")
                    if st.button("💾 Update Comment", key=f"save_edit_{post_id}"):
                        new_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        conn = sqlite3.connect(DB_PATH)
                        cur = conn.cursor()
                        cur.execute('''
                            UPDATE alerts SET comment=?, timestamp=? WHERE post_id=?
                        ''', (new_comment, new_ts, post_id))
                        conn.commit(); conn.close()
                        st.success("✅ Comment updated successfully.")
                        st.rerun()

                # Manual send email styled
                default_email = username if "@" in username else f"{username}@gmail.com"
                email_to = st.text_input("Email To:", value=default_email, key=f"manual_email_{post_id}")
                email_body = st.text_area(
                    "Email Body:",
                    value=f"Dear {username},\n\n{alert['comment']}\n", key=f"manual_body_{post_id}"
                )
                if st.button("📧 Send Email", key=f"send_manual_{post_id}"):
                    try:
                        # Convert plain body to HTML paragraphs
                        body_html = ''.join([f'<p style="font-size:16px; line-height:1.5;">{line}</p>' for line in email_body.splitlines()])
                        html_body = build_email_template(
                            title="Review Notification",
                            body_html=body_html
                        )
                        send_email(email_to, "Review Notification", html_body)
                        st.success(f"✅ Email sent to {email_to}")
                    except Exception as e:
                        st.error(f"❌ Failed to send email: {e}")

            else:
                st.markdown("---")
                colx1, colx2 = st.columns([3, 1])
                with colx1:
                    comment = st.text_area(f"Add Comment for ID {post_id}", key=f"comment_{post_id}")
                with colx2:
                    if st.button(f"✅ Review (Manual)", key=f"review_{post_id}"):
                        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
                        cur.execute(
                            '''INSERT INTO alerts (post_id, admin_username, comment, timestamp)
                               VALUES (?, ?, ?, ?)''',
                            (post_id, st.session_state.get("username", "admin"), comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        )
                        conn.commit(); conn.close()
                        st.success(f"Marked ID {post_id} as reviewed.")
                        st.rerun()
                    if st.button(f"🤖 Auto Review (ID {post_id})", key=f"auto_review_{post_id}"):
                        auto_review(post_id, username, post_text)
                        st.rerun()

    if reviewed_data:
        st.markdown("### 📤 Export Reviewed Posts")
        df = pd.DataFrame(reviewed_data)
        st.download_button(
            label="⬇ Download Reviewed Posts CSV",
            data=df.to_csv(index=False), file_name="reviewed_flagged_posts.csv", mime="text/csv"
        )

def show_export():
    st.title("📤 Export Data")
    st.write("Here you can export sentiment analysis data as a CSV or Excel file.")
    
    # Example dummy data
    df = pd.DataFrame({
        "Username": ["user1", "user2", "user3"],
        "Post": ["I love this!", "Not happy", "It’s okay"],
        "Sentiment": ["Positive", "Negative", "Neutral"]
    })

    st.dataframe(df)

    export_format = st.selectbox("Select format", ["CSV", "Excel"])
    if st.button("Download"):
        if export_format == "CSV":
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, "sentiment_data.csv", "text/csv")
        elif export_format == "Excel":
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="SentimentData")
                writer.save()
            st.download_button("Download Excel", buffer.getvalue(), "sentiment_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
# --- Main App ---
def app():
    start_scheduler()
    st.markdown("""
        <style>
            .css-1v3fvcr { padding-top: 0px !important; margin-top: 0px !important; }
            .css-1y4xxkc { margin-top: 0px !important; padding-top: 0px !important; }
            .css-1h6pdkz { margin-top: 0px !important; }
            h2, h3 { margin-top: 0px !important; padding-top: 0px !important; }
            .admin-title {
                font-size: 30px;
                font-weight: bold;
                color: #2f3d4b;
                padding-top: 20px;
                padding-bottom: 10px;
                margin-bottom: 0px;
            }
        </style>
    """, unsafe_allow_html=True)

    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""

    if not st.session_state.admin_logged_in:
        st.markdown("## 🔐 Admin Login")
        username = st.text_input("👤 Username")
        password = st.text_input("🔑 Password", type="password")
        if st.button("🔓 Login"):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.session_state.username = username
                st.success("✅ Logged in as admin.")
                st.rerun()
            else:
                st.error("❌ Invalid admin credentials.")
        return

    with st.sidebar:
        st.markdown("<div class='sidebar-title'>🛡️ Admin Panel</div>", unsafe_allow_html=True)
        if st.button("🚪 Logout"):
            st.session_state.admin_logged_in = False
            st.session_state.username = ""
            st.rerun()
        page = st.selectbox(
            "🌐 Navigate",
            ["📊 Dashboard", "👥 Manage Users", "🚨 Flagged Content", "📥 Export Data"],
            index=0
        )

    if page.startswith("📊"):
        show_dashboard()
    elif page.startswith("👥"):
        show_users()
    elif page.startswith("🚨"):
        show_flagged()
    else:
        show_export()


if __name__ == '__main__':
    app()
