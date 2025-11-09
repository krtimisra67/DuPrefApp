# main_app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import hashlib
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai  # Gemini client

# ---------------------- PAGE CONFIG ----------------------
st.set_page_config(page_title="🎓 DU Preference Maker", layout="wide")
load_dotenv()  # load .env in local / deployed environment if present

# ---------------------- UTILITY FUNCTIONS ----------------------
def make_hash(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password: str, hashed: str) -> bool:
    return make_hash(password) == hashed

def load_users(filepath: str = "users.csv") -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["username", "password"])

def save_users(df: pd.DataFrame, filepath: str = "users.csv"):
    df.to_csv(filepath, index=False)

@st.cache_data
def load_cutoff_data(filepath: str = "du_cutoff.csv") -> pd.DataFrame:
    """
    Expected CSV columns (case-insensitive): COLLEGE NAME, PROGRAM NAME, UR, OBC, SC, ST, EWS, PwBD
    If file not found, returns an empty DataFrame.
    """
    try:
        df = pd.read_csv(filepath)
        # normalize column names
        df.columns = [c.strip().upper() for c in df.columns]
        if "COLLEGE NAME" not in df.columns or "PROGRAM NAME" not in df.columns:
            st.warning("du_cutoff.csv found but missing required columns 'COLLEGE NAME' or 'PROGRAM NAME'.")
        # ensure numeric categories exist as numeric
        for cat in ["UR", "OBC", "SC", "ST", "EWS", "PWBD"]:
            if cat in df.columns:
                df[cat] = pd.to_numeric(df[cat], errors="coerce")
        return df
    except FileNotFoundError:
        return pd.DataFrame()

def filter_program_df(df: pd.DataFrame, program: str, girls_only: bool, girls_colleges: list) -> pd.DataFrame:
    if df.empty:
        return df
    filtered = df[df["PROGRAM NAME"].str.lower() == program.lower()].copy()
    if girls_only:
        filtered = filtered[filtered["COLLEGE NAME"].isin(girls_colleges)]
    return filtered

# ---------------------- GIRLS' COLLEGES LIST ----------------------
girls_colleges = [
    "Aditi Mahavidyalaya (W)", "Bhagini Nivedita College (W)", "Bharati College (W)",
    "Miranda House", "Gargi College (W)", "Lady Shri Ram College for Women (W)",
    "Lakshmibai College (W)", "Daulat Ram College (W)", "Indraprastha College for Women (W)",
    "Maitreyi College (W)", "Jesus & Mary College (W)", "Kamala Nehru College (W)",
    "Janki Devi Memorial College (W)", "Institute of Home Economics (W)",
    "Kalindi College (W)", "Shaheed Rajguru College of Applied Sciences for Women (W)",
    "Mata Sundri College for Women (W)", "Shyama Prasad Mukherjee College for Women (W)",
    "Vivekananda College (W)"
]

# ---------------------- GEMINI (Gemini Flash / Pro) SETUP ----------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # user wants .env approach
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        GEMINI_AVAILABLE = True
    except Exception:
        GEMINI_AVAILABLE = False
else:
    GEMINI_AVAILABLE = False

# ---------------------- STYLING & HEADER ----------------------
st.markdown("""
    <style>
        .title {text-align:center; font-size:2.1em; font-weight:700; color:#0b3d91;}
        .subtitle {text-align:center; color:#6b7280; margin-bottom:1.2rem;}
        .card {background:#ffffff; padding:12px; border-radius:10px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);}
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="title">🎓 DU Preference Maker</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Generate your DU preference list, get AI suggestions and analytics — powered by Gemini.</div>', unsafe_allow_html=True)

# ---------------------- SIDEBAR: LOGIN / SIGNUP ----------------------
st.sidebar.header("🔐 Account")
users_df = load_users()

auth_mode = st.sidebar.radio("Choose", ["Login", "Sign Up"])
if auth_mode == "Sign Up":
    st.sidebar.subheader("Create account")
    new_user = st.sidebar.text_input("Username", key="signup_user")
    new_password = st.sidebar.text_input("Password", type="password", key="signup_pw")
    if st.sidebar.button("Create Account"):
        if not new_user or not new_password:
            st.sidebar.warning("Please enter username and password.")
        elif new_user in users_df["username"].values:
            st.sidebar.error("Username already exists. Choose another.")
        else:
            new_row = pd.DataFrame([[new_user, make_hash(new_password)]], columns=["username", "password"])
            users_df = pd.concat([users_df, new_row], ignore_index=True)
            save_users(users_df)
            st.sidebar.success("Account created! Please login from the Login tab.")

elif auth_mode == "Login":
    st.sidebar.subheader("Login")
    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pw")
    if st.sidebar.button("Login"):
        if username in users_df["username"].values:
            stored_hash = users_df.loc[users_df["username"] == username, "password"].values[0]
            if check_hash(password, stored_hash):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.sidebar.success(f"Welcome, {username} 👋")
                time.sleep(0.6)
                st.experimental_rerun()
            else:
                st.sidebar.error("Incorrect password.")
        else:
            st.sidebar.error("Username not found. Please sign up.")

# ---------------------- If logged in: show main app ----------------------
if "logged_in" in st.session_state and st.session_state["logged_in"]:
    username = st.session_state.get("username", "User")
    st.sidebar.markdown(f"**Signed in:** {username}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

    # Load cutoff data (from CSV in project root)
    df_cutoff = load_cutoff_data()

    # TABS: Home, AI Suggestions, Analytics, Admin Upload
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Home", "🤖 AI Suggestions", "📊 Analytics", "⚙️ Upload Data"])

    # ---------------------- TAB 1: Home (Preference Finder) ----------------------
    with tab1:
        st.header("📋 Preference Finder")
        if df_cutoff.empty:
            st.warning("Cutoff dataset (du_cutoff.csv) not found. Go to 'Upload Data' tab to upload the CSV.")
        else:
            # Basic inputs on left column, results on right
            left, right = st.columns([1, 2])
            with left:
                marks = st.number_input("🎯 CUET Score", min_value=0.0, max_value=1250.0, value=600.0, step=0.5)
                category = st.selectbox("🏷 Category", ["UR", "OBC", "SC", "ST", "EWS", "PWBD"])
                program = st.selectbox("📚 Program", sorted(df_cutoff["PROGRAM NAME"].unique()))
                girls_only = st.checkbox("🎀 Show only Girls’ Colleges", value=False)
                find_button = st.button("🔍 Generate Preference List")

            with right:
                st.info("💡 Results will show here. 'Marks Above Cutoff' indicates how many marks your score exceeds the cutoff by.")

            if find_button:
                with st.spinner("🔎 Analyzing cutoffs..."):
                    prog_df = filter_program_df(df_cutoff, program, girls_only, girls_colleges)

                    if prog_df.empty:
                        st.warning("No data found for selected program (or dataset missing).")
                    elif category not in prog_df.columns:
                        st.error(f"Cutoff category '{category}' not available for this program.")
                    else:
                        prog_df = prog_df.dropna(subset=[category])
                        eligible_df = prog_df[prog_df[category] <= marks].copy()
                        if eligible_df.empty:
                            st.warning("You did not meet the cutoff for this program in any college.")
                            # show nearest matches
                            nearest = prog_df.sort_values(by=category).head(6)
                            st.markdown("### 🔎 Nearest cutoffs (for reference)")
                            st.dataframe(nearest[["COLLEGE NAME", "PROGRAM NAME", category]].rename(columns={category:"Cutoff"}))
                        else:
                            eligible_df["Marks Above Cutoff"] = marks - eligible_df[category]
                            eligible_df = eligible_df.sort_values(by="Marks Above Cutoff", ascending=False)
                            eligible_df.insert(0, "Rank", range(1, len(eligible_df) + 1))
                            st.success(f"🎯 Eligible Colleges for **{program} ({category})**" + (" — Girls' Colleges only" if girls_only else ""))
                            # summary metrics
                            col1, col2, col3 = st.columns(3)
                            col1.metric("🏫 Eligible Colleges", len(eligible_df))
                            col2.metric("📈 Highest Margin", f"{eligible_df['Marks Above Cutoff'].max():.1f} marks")
                            col3.metric("📉 Lowest Margin", f"{eligible_df['Marks Above Cutoff'].min():.1f} marks")

                            st.dataframe(
                                eligible_df[["Rank", "COLLEGE NAME", "PROGRAM NAME", category, "Marks Above Cutoff"]],
                                use_container_width=True,
                                hide_index=True
                            )

                            csv = eligible_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                label="📥 Download Preference List (CSV)",
                                data=csv,
                                file_name=f"DU_Preferences_{program.replace(' ', '_')}_{category}{'_Girls' if girls_only else ''}.csv",
                                mime="text/csv"
                            )

                            # Provide Gemini suggestion summary (if available)
                            if GEMINI_AVAILABLE:
                                st.markdown("### 🤖 Gemini Counsel")
                                with st.spinner("Generating a short counseling note via Gemini..."):
                                    try:
                                        model = genai.GenerativeModel("gemini-2.0-flash")
                                        nearby_colleges = ", ".join(eligible_df["COLLEGE NAME"].head(6).tolist())
                                        prompt = f"""
                                        You are a friendly Delhi University admissions counsellor.
                                        The student scored {marks} (category: {category}) and is eligible for these colleges:
                                        {nearby_colleges}

                                        Give a short (3-4 sentences) practical counseling note about:
                                        1) Why these colleges are good fits,
                                        2) Short next-step advice for the student.
                                        Tone: encouraging and concise.
                                        """
                                        response = model.generate_content(prompt)
                                        st.info(response.text.strip())
                                    except Exception as e:
                                        st.error(f"Could not generate Gemini recommendation: {e}")
                            else:
                                st.info("Gemini API key not found or Gemini unavailable. To enable AI suggestions, add GOOGLE_API_KEY to your .env.")

    # ---------------------- TAB 2: AI Suggestions (upload + freeform) ----------------------
    with tab2:
        st.header("🤖 AI Suggestions")
        st.write("You can upload your college dataset and ask Gemini for preference suggestions or freeform counseling.")
        uploaded_file_ai = st.file_uploader("Upload CSV for AI to reference (optional)", type=["csv"], key="ai_upload")

        ai_df = None
        if uploaded_file_ai is not None:
            ai_df = pd.read_csv(uploaded_file_ai)
            st.success("✅ AI reference file uploaded")
            st.dataframe(ai_df.head(10))

        st.subheader("Describe your goals")
        user_goal = st.text_area("E.g., 'I scored 620 in CUET. I want top BSc Computer Science options in DU.'", height=120)
        model_select = st.selectbox("Gemini Model (if available)", ["gemini-2.0-flash", "gemini-pro"])
        if st.button("Generate AI Suggestions (Gemini)"):
            if not GEMINI_AVAILABLE:
                st.error("Gemini is not configured. Ensure GOOGLE_API_KEY is set in your .env and restart.")
            elif not user_goal.strip():
                st.warning("Please write your goals before generating suggestions.")
            else:
                with st.spinner("🤖 Generating suggestions..."):
                    try:
                        model = genai.GenerativeModel(model_select)
                        context = ""
                        if ai_df is not None:
                            context = f"Reference dataset (first 10 rows):\n{ai_df.head(10).to_string(index=False)}\n\n"
                        prompt = f"""
                        You are an experienced DU admissions counselor. The user's goal is:
                        {user_goal}

                        {context}
                        Provide:
                        1) Top 3 preference suggestions (college + why),
                        2) 2 concrete next steps the student can take.
                        Keep it concise (4-6 short paragraphs).
                        """
                        response = model.generate_content(prompt)
                        st.markdown("### 🧭 Gemini's Suggestion")
                        st.write(response.text.strip())
                    except Exception as e:
                        st.error(f"AI generation failed: {e}")

    # ---------------------- TAB 3: Analytics ----------------------
    with tab3:
        st.header("📊 Analytics Dashboard")
        if df_cutoff.empty:
            st.info("Upload du_cutoff.csv in 'Upload Data' tab to enable analytics.")
        else:
            # Small controls for analytics
            st.caption("Interactive charts to explore cutoffs and program distributions.")
            analytics_program = st.selectbox("Select Program for visualization", sorted(df_cutoff["PROGRAM NAME"].unique()))
            analytics_category = st.selectbox("Select Category", ["UR", "OBC", "SC", "ST", "EWS", "PWBD"])

            if st.button("Show Analytics"):
                prog_df = df_cutoff[df_cutoff["PROGRAM NAME"].str.lower() == analytics_program.lower()].dropna(subset=[analytics_category])
                if prog_df.empty:
                    st.warning("No data available for this program/category.")
                else:
                    # Top 10 colleges by cutoff (lowest cutoff = more accessible)
                    top10 = prog_df.sort_values(by=analytics_category).head(10)
                    st.subheader(f"Top 10 Colleges by {analytics_category} cutoff (lower is more accessible)")
                    st.dataframe(top10[["COLLEGE NAME", analytics_category]].rename(columns={analytics_category:"Cutoff"}), use_container_width=True)

                    # Horizontal bar plot of the top 10
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.barh(top10["COLLEGE NAME"], top10[analytics_category])
                    ax.set_xlabel("Cutoff Marks")
                    ax.set_title(f"{analytics_program} - {analytics_category} (Top 10)")
                    plt.tight_layout()
                    st.pyplot(fig)

                    # Aggregate: avg cutoff by college (if dataset contains multiple programs per college)
                    st.subheader("College-wise Average Cutoff (sample)")
                    avg_cutoff = df_cutoff.groupby("COLLEGE NAME")[analytics_category].mean().dropna().sort_values().head(10)
                    fig2, ax2 = plt.subplots(figsize=(8, 4))
                    ax2.barh(avg_cutoff.index, avg_cutoff.values)
                    ax2.set_xlabel("Average Cutoff")
                    ax2.set_title("College-wise Average Cutoff (sample)")
                    plt.tight_layout()
                    st.pyplot(fig2)

    # ---------------------- TAB 4: Upload Data (Admin) ----------------------
    with tab4:
        st.header("⚙️ Upload / Replace Data")
        st.write("Upload `du_cutoff.csv` to update cutoff dataset. This will overwrite local du_cutoff.csv used by the app.")
        uploaded_cutoff = st.file_uploader("Upload du_cutoff.csv (with columns: COLLEGE NAME, PROGRAM NAME, UR, OBC, SC, ST, EWS, PwBD)", type=["csv"], key="upload_cutoff")
        if uploaded_cutoff is not None:
            try:
                new_df = pd.read_csv(uploaded_cutoff)
                new_df.columns = [c.strip().upper() for c in new_df.columns]
                # save to disk
                new_df.to_csv("du_cutoff.csv", index=False)
                st.success("du_cutoff.csv uploaded and saved. Reloading data...")
                # clear cache and reload
                load_cutoff_data.clear()
                time.sleep(0.8)
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Failed to upload file: {e}")

    # ---------------------- FOOTER ----------------------
    st.markdown("---")
    st.caption("Made with ❤️ by Kriti, Sapna & Anushka | DU Preference Maker 2025 — aligned with CSAS(UG) 2025 guidelines")

else:
    # Not logged in
    st.info("Please sign up or log in via the sidebar to access the DU Preference Maker.")
    st.markdown("---")
    st.caption("If you're new: Sign up in the sidebar (creates a local users.csv).")
