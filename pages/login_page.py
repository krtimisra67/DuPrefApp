import streamlit as st
import pandas as pd
import hashlib
import os

# ----------------- HELPER FUNCTIONS -----------------
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed):
    return make_hash(password) == hashed

def load_users():
    if os.path.exists("users.csv"):
        return pd.read_csv("users.csv")
    else:
        return pd.DataFrame(columns=["username", "password"])

def save_users(df):
    df.to_csv("users.csv", index=False)

# ----------------- PAGE SETUP -----------------
st.set_page_config(page_title="🎓 DU Preference Maker Login", layout="centered")

st.title("🎓 DU Preference Maker - Login Portal")

menu = ["Login", "Signup"]
choice = st.sidebar.selectbox("Menu", menu)

# Always load fresh users
users_df = load_users()

# ----------------- LOGIN -----------------
if choice == "Login":
    st.subheader("🔑 Login to your account")
    username = st.text_input("👤 Username")
    password = st.text_input("🔒 Password", type="password")

    if st.button("Login"):
        if username in users_df["username"].values:
            stored_hash = users_df.loc[users_df["username"] == username, "password"].values[0]
            if check_hash(password, stored_hash):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"✅ Welcome back, {username}!")
                st.switch_page("main_app.py")
            else:
                st.error("❌ Incorrect password")
        else:
            st.error("⚠️ User not found! Please sign up first.")

# ----------------- SIGNUP -----------------
elif choice == "Signup":
    st.subheader("📝 Create a new account")

    new_user = st.text_input("👤 Choose a Username")
    new_pass = st.text_input("🔒 Choose a Password", type="password")
    confirm_pass = st.text_input("🔁 Confirm Password", type="password")

    if st.button("Create Account"):
        if new_pass != confirm_pass:
            st.error("❌ Passwords do not match!")
        elif new_user in users_df["username"].values:
            st.warning("⚠️ Username already exists.")
        else:
            # Reload users before saving (ensures freshness)
            users_df = load_users()
            new_data = pd.DataFrame([[new_user, make_hash(new_pass)]], columns=["username", "password"])
            users_df = pd.concat([users_df, new_data], ignore_index=True)
            save_users(users_df)
            st.success("✅ Account created successfully! Please login now.")
