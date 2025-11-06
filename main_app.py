import streamlit as st
import pandas as pd

# ---------------------- LOGIN CHECK ----------------------
st.set_page_config(page_title="🎓 DU Preference Maker", layout="wide")

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
    df = pd.read_csv("du_cutoff.csv")  # Replace with your CSV path
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

# ---------------------- SIDEBAR FORM ----------------------
with st.sidebar:
    st.header("🧮 Enter Your Details")
    marks = st.number_input("🎯 CUET Score", min_value=0.0, max_value=1000.0, value=600.0, step=0.5)
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

            if eligible_df.empty:
                st.warning("⚠️ No colleges found where you meet the cutoff. Try adjusting your score or category.")
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
