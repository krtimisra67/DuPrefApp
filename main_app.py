import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import google.generativeai as genai  # ✅ Correct import for Gemini Flash 2.0

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="🎓 DU Preference Maker", layout="wide")

# ---------------------- LOAD .ENV & API ----------------------
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ GOOGLE_API_KEY not set. Please create a .env file with your Gemini API key.")
    st.stop()

# ✅ Configure Gemini Flash 2.0
genai.configure(api_key=api_key)

# ---------------------- LOGIN CHECK ----------------------
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    st.warning("⚠️ Please log in first to access the Preference Maker.")
    st.info("🔐 Redirecting you to the login page...")
    st.stop()

# ---------------------- HEADER ----------------------
st.title("🎓 DU Preference Maker")
st.markdown(f"""
#### Welcome, **{st.session_state['username']}** 👋  
Find your eligible colleges based on July 2025 CUET cutoffs and CSAS(UG) 2025 rules.
""")

# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_data():
    df = pd.read_csv("du_cutoff.csv")
    df.columns = [c.strip().upper() for c in df.columns]
    df["PROGRAM NAME"] = df["PROGRAM NAME"].astype(str)
    for cat in ["UR", "OBC", "SC", "ST", "EWS", "PwBD"]:
        if cat in df.columns:
            df[cat] = pd.to_numeric(df[cat], errors="coerce")
    return df

df = load_data()

# ---------------------- GIRLS' COLLEGES ----------------------
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

# ---------------------- GEMINI FLASH 2.0 FUNCTION ----------------------
def get_gemini_suggestion(program, category, marks, eligible_df, full_df):
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")

        nearby_df = full_df[
            (full_df["PROGRAM NAME"].str.lower() == program.lower()) &
            (abs(full_df[category] - marks) <= 10)
        ]

        if not nearby_df.empty:
            nearby_colleges = ", ".join(nearby_df["COLLEGE NAME"].head(10).tolist())
            context_text = f"Some colleges close to your score are: {nearby_colleges}."
        else:
            context_text = "No nearby cutoffs found, but many students are in a similar range."

        prompt = f"""
        You are a helpful and friendly Delhi University admission counsellor.

        The student has scored {marks} in CUET and belongs to category {category}.
        They are applying for the program: **{program}**.
        Based on the cutoff analysis, they are eligible for the following colleges:
        {', '.join(eligible_df['COLLEGE NAME'].head(10).tolist())}.

        Give an informative, encouraging, and human-like response that covers:
        1. A short overview of what the {program} course is about and its academic scope.
        2. Why the above colleges are good options for this program (based on their reputation or focus areas).
        3. What the student can do **after completing this course** — career paths, higher studies, or research opportunities.
        4. End with a motivating closing line to keep the student confident and inspired.

        Keep it concise (around 3–4 short paragraphs) and friendly in tone.
        """

        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        return f"⚠️ Could not generate AI suggestion: {e}"

# ---------------------- SIDEBAR FORM ----------------------
with st.sidebar:
    st.header("🧮 Enter Your Details")
    marks = st.number_input("🎯 CUET Score", min_value=0.0, max_value=1250.0, value=600.0, step=0.5)
    category = st.selectbox("🏷️ Category", ["UR", "OBC", "SC", "ST", "EWS", "PwBD"])
    program = st.selectbox("📚 Program", sorted(df["PROGRAM NAME"].unique()))
    girls_only = st.checkbox("🎀 Show only Girls’ Colleges", value=False)
    submit_button = st.button("🔍 Generate Preference List")

    st.markdown("---")
    st.caption("💡 Only colleges you are eligible for will appear below.")

# ---------------------- MAIN LOGIC ----------------------
if submit_button:
    try:
        filtered_df = df[df["PROGRAM NAME"].str.lower() == program.lower()].copy()

        if girls_only:
            filtered_df = filtered_df[filtered_df["COLLEGE NAME"].isin(girls_colleges)]

        if category not in filtered_df.columns:
            st.error(f"⚠️ Cutoff data for category '{category}' not found for this program.")
        else:
            filtered_df = filtered_df.dropna(subset=[category])
            eligible_df = filtered_df[filtered_df[category] <= marks].copy()

            # ---------------------- IF NO ELIGIBLE COLLEGES ----------------------
            if eligible_df.empty:
                st.warning("⚠️ You didn't meet the cutoff for this program at any DU college.")

                # ✅ Gemini Flash 2.0 fallback suggestion
                try:
                    model = genai.GenerativeModel("gemini-2.0-flash")

                    nearby_df = filtered_df.sort_values(by=category, ascending=True).head(5)
                    nearby_list = ", ".join(nearby_df["COLLEGE NAME"].tolist())

                    prompt = f"""
                    You are a supportive Delhi University admission counsellor.

                    The student scored {marks} in CUET and belongs to category {category}.
                    They are applying for **{program}**, but their score is below the cutoff.

                    Please provide:
                    1. A short motivational message acknowledging their effort.
                    2. Suggest 2–3 related programs they can consider (based on DU offerings).
                    3. Mention some nearby colleges like {nearby_list} where similar programs exist.
                    4. Offer advice on how to prepare or upskill for next year, or explore alternative career paths.

                    Tone: warm, realistic, and encouraging.
                    Length: 3–4 short paragraphs.
                    """

                    response = model.generate_content(prompt)
                    st.markdown("### 🌟 Guidance from Gemini Flash 2.0")
                    st.info(response.text.strip())

                except Exception as e:
                    st.error(f"⚠️ Could not generate guidance: {e}")

            # ---------------------- IF ELIGIBLE COLLEGES FOUND ----------------------
            else:
                eligible_df["Marks Above Cutoff"] = marks - eligible_df[category]
                eligible_df = eligible_df.sort_values(by="Marks Above Cutoff", ascending=False)
                eligible_df.insert(0, "Rank", range(1, len(eligible_df) + 1))

                st.success(f"🎯 Eligible Colleges for **{program} ({category})**"
                           + (" (Girls’ Colleges only)" if girls_only else ""))

                st.dataframe(
                    eligible_df[["Rank", "COLLEGE NAME", "PROGRAM NAME", category, "Marks Above Cutoff"]],
                    use_container_width=True,
                    hide_index=True
                )

                st.info("💡 'Marks Above Cutoff' shows how many marks your score exceeds the cutoff by.")

                csv = eligible_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Preference List (CSV)",
                    data=csv,
                    file_name=f"DU_Preferences_{program.replace(' ', '_')}_{category}{'_Girls' if girls_only else ''}.csv",
                    mime="text/csv"
                )

                # ---------------------- GEMINI FLASH 2.0 ----------------------
                st.markdown("### 🤖 Gemini Flash 2.0 Suggestion")
                gemini_advice = get_gemini_suggestion(program, category, marks, eligible_df, df)
                st.info(gemini_advice)

    except Exception as e:
        st.error(f"⚠️ Unexpected error: {e}")

# ---------------------- LOGOUT BUTTON ----------------------
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Logout"):
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.success("🔒 Logged out successfully!")
    st.switch_page("pages/login_page.py")

# ---------------------- FOOTER ----------------------
st.markdown("---")
st.caption("Made with ❤️ by **Kriti, Sapna & Anushka** | DU Preference Maker 2025 – aligned with CSAS(UG) 2025 guidelines")
