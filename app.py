import streamlit as st
from backend.database import create_db
from frontend import home, dashboard, analysis, alerts, admin_panel
import os
import time
from datetime import timedelta

# ─────────────────────────────────────────────────────
# 1) Ensure your SQLite tables exist
# ─────────────────────────────────────────────────────
create_db()

# ─────────────────────────────────────────────────────
# 2) Streamlit Page Configuration
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Social Media Sentiment Health Analysis",
    layout="centered",
)

# ─────────────────────────────────────────────────────
# 3) Load custom CSS (if available)
# ─────────────────────────────────────────────────────
css_path = os.path.join("assets", "styles.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────
# 4) Initialize Session State
# ─────────────────────────────────────────────────────
default_states = {
    "logged_in_user": None,
    "logged_in": False,
    "admin_logged_in": False,
    "admin_mode": False,
    "last_activity": time.time(),  # Track last activity time
}

for key, value in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ─────────────────────────────────────────────────────
# 5) Session Timeout Logic
# ─────────────────────────────────────────────────────
SESSION_TIMEOUT = timedelta(minutes=15)  # Set timeout duration

def check_session_timeout():
    """Check if session has expired based on inactivity."""
    current_time = time.time()
    last_activity = st.session_state.get("last_activity", current_time)

    # Check if the session has expired
    if current_time - last_activity > SESSION_TIMEOUT.total_seconds():
        st.session_state.logged_in = False  # Log out user if session expired
        st.session_state.admin_logged_in = False  # Log out admin if session expired
        st.session_state.logged_in_user = None
        st.session_state.admin_mode = False

    # Update the last activity timestamp
    st.session_state["last_activity"] = current_time

# ─────────────────────────────────────────────────────
# 6) Main Navigation Function
# ─────────────────────────────────────────────────────
def main():
    # ✅ Check for session timeout
    check_session_timeout()

    # ✅ Redirect to home if not logged in
    if not st.session_state.logged_in_user and not st.session_state.admin_logged_in:
        home.app()
        return

    # ✅ Admin Panel Mode
    if st.session_state.admin_logged_in:
        admin_panel.app()
        return

    # ✅ User Mode: Sidebar + Navigation
    logo_path = os.path.join("assets", "logo.png")
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)

    menu = ["Home", "Dashboard", "Analyze", "Alerts"]
    choice = st.sidebar.selectbox("Navigation", menu)

    # Update last activity timestamp when a user interacts
    if choice:
        st.session_state["last_activity"] = time.time()

    # Navigate to selected page
    if choice == "Home":
        home.app()
    elif choice == "Dashboard":
        dashboard.app()
    elif choice == "Analyze":
        analysis.app()
    elif choice == "Alerts":
        alerts.app()

    # ✅ Sidebar Logout Button
    with st.sidebar:
        if st.button("🚪 Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("You have logged out.")
            time.sleep(1)
            st.rerun()  # ✅ Using latest method

# ─────────────────────────────────────────────────────
# 7) App Entry Point
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
