import streamlit as st
from backend import database

def login_user(username, password):
    # Validate user credentials using the database function
    if database.validate_user(username, password):
        st.success(f"Welcome {username}!")
    else:
        st.error("Invalid credentials")

def register_user(username, email, password):
    # Attempt to create a new user using the database function
    if database.create_user(username, email, password):
        st.success("Registration successful!")
    else:
        st.error("User already exists")
