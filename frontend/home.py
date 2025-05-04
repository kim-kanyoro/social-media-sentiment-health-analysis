import streamlit as st
from backend import database
import time

def admin_panel():
    st.markdown("## 👨‍💼 Welcome to the Admin Panel")
    st.write("You can manage users, view analytics, and more!")

def app():
    # Session Initialization
    for key, value in {
        "show_login": True,
        "logged_in_user": None,
        "otp_sent": False,
        "dark_mode": False,
        "logged_in": False,
        "admin_logged_in": False,
        "admin_mode": False,
    }.items():
        if key not in st.session_state:
            st.session_state[key] = value

    def switch_form():
        st.session_state.show_login = not st.session_state.show_login
        st.session_state.otp_sent = False

    def toggle_theme():
        st.session_state.dark_mode = not st.session_state.dark_mode

    # Dark Theme Styling
    if st.session_state.dark_mode:
        st.markdown("""<style>/* your theme CSS */</style>""", unsafe_allow_html=True)

    st.sidebar.markdown("🌓 **Theme**")
    st.sidebar.button("Toggle Dark Mode", on_click=toggle_theme)

    # Show the admin toggle ONLY when no one is logged in
    if not st.session_state.get("logged_in") and not st.session_state.get("admin_logged_in"):
        st.markdown("🔁 **Toggle between User and Admin Login**")
        admin_toggle = st.checkbox("Switch to Admin Login", key="admin_mode_checkbox")
        st.session_state["admin_mode"] = admin_toggle
    else:
        st.session_state["admin_mode"] = False  # reset if already logged in

    # ✅ Admin Panel View
    if st.session_state["admin_logged_in"]:
        admin_panel()
        return

    # 👤 User or Admin Login UI
    if not st.session_state.logged_in_user:
        st.markdown("<h1 style='font-size:36px; color: #1E88E5;'>🧠 Social Media Sentiment Health Analysis</h1>", unsafe_allow_html=True)

        if st.session_state["admin_mode"]:
            st.markdown("You are now in **Admin Login Mode**.")
        else:
            st.markdown("You are in **User Login Mode**.")

        # 🔐 Admin Login
        if st.session_state["admin_mode"]:
            st.subheader("🔐 Admin Login")
            admin_user = st.text_input("Admin Username", key="admin_username")
            admin_pass = st.text_input("Admin Password", type="password", key="admin_password")

            if st.button("Login as Admin"):
                if admin_user == "admin" and admin_pass == "admin123":
                    st.success("✅ Admin login successful.")
                    st.session_state["admin_logged_in"] = True
                    st.session_state["logged_in_user"] = None
                    st.session_state["logged_in"] = False
                    time.sleep(1)
                    st.session_state["admin_mode"] = False
                    st.rerun()
                else:
                    st.error("❌ Invalid admin credentials.")

        # 🔐 Regular User Login
        elif st.session_state.show_login:
            st.subheader("🔐 User Login")
            username = st.text_input("Enter Email!", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login"):
                if username.strip() == "" or password.strip() == "":
                    st.warning("Please fill in all fields.")
                else:
                    user = database.login_user(username, password)
                    if user:
                        st.session_state.logged_in_user = {
                            "id": user[0],
                            "username": user[1],
                            "email": user[2],
                        }
                        st.session_state["logged_in"] = True
                        st.session_state["user_email"] = user[2]
                        st.session_state["username"] = user[1]
                        st.success(f"Welcome, {username}!")
                        time.sleep(1)
                        st.rerun()
                        return

            if st.button("Forgot Password?"):
                st.session_state.otp_sent = True

            if st.session_state.otp_sent:
                st.info("🔑 Simulating OTP verification...")
                otp_input = st.text_input("Enter OTP", key="otp_input")
                if st.button("Verify OTP"):
                    st.success("✅ OTP Verified.")

            st.button("Go to Sign Up", on_click=switch_form)

        # 📝 Sign Up
        else:
            st.subheader("📝 Sign Up")
            username = st.text_input("Enter Username!", key="signup_username")
            email = st.text_input("Enter Email!", key="signup_email")
            confirm_email = st.text_input("Confirm Email!", key="confirm_email")
            password = st.text_input("Enter Password!", type="password", key="signup_password")

            if st.button("Sign Up"):
                if not username or not email or not confirm_email or not password:
                    st.warning("Please fill in all fields.")
                elif email != confirm_email:
                    st.error("Emails do not match.")
                elif database.user_exists(username):
                    st.warning("Username already exists.")
                else:
                    success = database.create_user(username, email, password)
                    if success:
                        st.success("✅ Registration successful!")
                        st.session_state.show_login = True
                    else:
                        st.error("🚫 Email already exists or an error occurred.")

            st.button("Go to Login", on_click=switch_form)

        st.markdown("""<div class="footer">© 2025 Social Media Sentiment Health Analysis. All rights reserved.</div>""", unsafe_allow_html=True)

    # ✅ User Dashboard
       # ✅ User Dashboard
    if st.session_state.logged_in_user:
        with st.sidebar:
            pass  # Sidebar available for future enhancements

        st.markdown("---")
        st.markdown("### 🧠 About the System")
        st.markdown("""
        Welcome to the **Social Media Sentiment Health Analysis** platform!

        This system allows you to:
        - 📌 **Analyze** your social media posts using AI-powered sentiment analysis.
        - ⚠️ **Detect and flag** emotionally sensitive or negative content (e.g., stress, anxiety).
        - 📈 **Track sentiment trends** over time through visual insights.
        - 🗃️ **Access history** of past analyses including flagged content.
        - 🧘 **Receive support tips and suggestions** based on your emotional state.
        - 🛡️ Allow admins to review and provide feedback on flagged posts.

        Our goal is to help you better understand your emotional well-being based on your online activity — all in a private and supportive environment.
        """)

        st.markdown("🚧 *(Features coming soon: real-time post analysis, mood graphs, and more!)*")
