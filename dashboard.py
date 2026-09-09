import os
import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="CAST | PR Orchestrator", layout="wide", initial_sidebar_state="collapsed")

# Inject Custom CSS for the redesign
import base64
import os

global_bg_css = ""
if os.path.exists("overall.png"):
    with open("overall.png", "rb") as f:
        encoded_overall = base64.b64encode(f.read()).decode('utf-8')
    global_bg_css = f"""
    .stApp, [data-testid="stAppViewContainer"] {{
        background-image: linear-gradient(rgba(14, 14, 16, 0.85), rgba(14, 14, 16, 0.85)), url("data:image/png;base64,{encoded_overall}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}
    """
else:
    global_bg_css = """
    .stApp {
        background-color: #0e0e10;
    }
    """

# Inject Custom CSS for the redesign
st.markdown(f"""<style>
{global_bg_css}
/* Base Dark Theme Overrides */
.stApp {{
    color: #e0e0e0;
}}
/* Hide Streamlit default header, toolbar (deploy button), hamburger menu, and footer */
[data-testid="stHeader"] {{
    display: none !important;
}}
[data-testid="stToolbar"] {{
    display: none !important;
}}
#MainMenu {{
    display: none !important;
}}
footer {{
    display: none !important;
}}
/* Red accents for primary buttons */
div.stButton > button[kind="primary"] {{
    background-color: #D32F2F;
    color: white;
    border: none;
}}
div.stButton > button[kind="primary"]:hover {{
    background-color: #B71C1C;
}}
/* Header typography */
.cast-header {{
    font-size: 3.5rem;
    font-weight: 900;
    letter-spacing: 2px;
    margin-bottom: 0px;
    color: #ffffff;
    line-height: 1.1;
}}
.cast-subtitle {{
    font-size: 0.9rem;
    color: #D32F2F;
    margin-top: 0px;
    margin-bottom: 20px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}}
/* Hide default sidebar nav completely to force our top nav */
[data-testid="collapsedControl"] {{
    display: none;
}}
section[data-testid="stSidebar"] {{
    display: none;
}}
/* Custom Card Layouts */
.approval-card {{
    background-color: rgba(26, 26, 28, 0.6);
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid #D32F2F;
    margin-bottom: 15px;
}}
</style>""", unsafe_allow_html=True)

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cast-506804")

@st.cache_resource
def get_db():
    return firestore.Client(project=PROJECT_ID)

db = get_db()

# Real Firebase Authentication (REST API)
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

if "role" not in st.session_state:
    st.session_state["role"] = None
if "uid" not in st.session_state:
    st.session_state["uid"] = None
if "email" not in st.session_state:
    st.session_state["email"] = None

def login():
    import base64
    import os
    
    bg_css = """<style>
/* Fit to screen, hide scrollbar */
html, body, [data-testid="stAppViewContainer"] {
    overflow: hidden !important;
    height: 100vh !important;
}
</style>"""
    
    if os.path.exists("HOMEPAGE.png"):
        with open("HOMEPAGE.png", "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        
        bg_css += f"""<style>
.stApp, [data-testid="stAppViewContainer"] {{
    background-image: url("data:image/png;base64,{encoded}") !important;
    background-size: cover !important;
    background-position: center !important;
    background-repeat: no-repeat !important;
}}
.block-container {{
    background: transparent !important;
    padding-top: 2rem !important;
}}
</style>"""
    else:
        st.warning("⚠️ Waiting for 'HOMEPAGE.png' to be placed in the project folder...")
        
    st.markdown(bg_css, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
        <p class='cast-header'>CAST</p>
        <p class='cast-subtitle'>Crisis Analysis & Strategy Tracker</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.write("") # Left empty so the HOMEPAGE.png background image shows through clearly
    with col2:
        st.markdown("<h1 style='margin-bottom: 0;'>Welcome Back</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #D32F2F; font-size: 0.9rem; font-weight: bold; margin-top: 0;'>Executive access only</p>", unsafe_allow_html=True)
        st.write("")
        
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        
        st.write("")
        if st.button("Secure Login", type="primary", use_container_width=True):
            if not FIREBASE_WEB_API_KEY:
                st.error("Missing FIREBASE_WEB_API_KEY in environment variables.")
                return
                
            # 1. Authenticate via Firebase REST API
            import requests
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
            payload = {"email": email, "password": pwd, "returnSecureToken": True}
            
            resp = requests.post(url, json=payload)
            if resp.status_code != 200:
                st.error(f"Authentication failed: {resp.json().get('error', {}).get('message', 'Unknown error')}")
                return
                
            uid = resp.json().get("localId")
            
            # 2. Check Role in Firestore (Governance Gating)
            user_doc = db.collection("users").document(uid).get()
            if not user_doc.exists:
                st.error("User document not found in Firestore. Access Denied.")
                return
                
            role = user_doc.to_dict().get("role")
            if role != "executive":
                st.error(f"Governance Check Failed: Your role is '{role}'. Executives only.")
                return
                
            # Success
            st.session_state["role"] = role
            st.session_state["uid"] = uid
            st.session_state["email"] = email
            st.rerun()

if st.session_state["role"] != "executive":
    login()
    st.stop()

# --- TOP NAVIGATION (Re-skin) ---
col_logo, col_nav, col_user = st.columns([1.5, 3, 1.5], vertical_alignment="bottom")
with col_logo:
    st.markdown("<p class='cast-header' style='font-size: 2.5rem;'>CAST</p>", unsafe_allow_html=True)
    st.markdown("<p class='cast-subtitle' style='font-size: 0.7rem;'>Crisis Analysis & Strategy Tracker</p>", unsafe_allow_html=True)
with col_nav:
    page = st.radio("Nav", ["Dashboard", "Register Campaign", "Pending Approvals"], horizontal=True, label_visibility="collapsed")
with col_user:
    user_initial = st.session_state["email"][0].upper() if st.session_state["email"] else "E"
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 12px; padding-bottom: 25px;">
        <span style="font-size: 0.9rem; color: #aaa;">{st.session_state['email']}</span>
        <div style="width: 32px; height: 32px; border-radius: 50%; background-color: #D32F2F; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid #555;">
            {user_initial}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<hr style='margin-top: -10px; border-color: #333;'>", unsafe_allow_html=True)

# --- PAGE ROUTING ---
if page == "Register Campaign":
    col_form, col_image = st.columns([1, 1.2])
    with col_form:
        st.markdown("<h2 style='margin-top: 0;'>Register New Film Campaign</h2>", unsafe_allow_html=True)
        st.write("Enter the core details to initialize real-time PR monitoring.")
        st.write("")
        with st.form("campaign_form"):
            title = st.text_input("Movie Title")
            cast = st.text_input("Key Cast (comma-separated)")
            st.write("")
            submitted = st.form_submit_button("Start Monitoring", type="primary", use_container_width=True)
            if submitted and title:
                db.collection("campaigns").add({
                    "movie_title": title,
                    "cast": [c.strip() for c in cast.split(",") if c.strip()],
                    "status": "active",
                    "last_run_status": "idle",
                    "created_at": firestore.SERVER_TIMESTAMP
                })
                st.success(f"Campaign '{title}' registered successfully!")
    with col_image:
        hola_bg = "linear-gradient(135deg, #2a0000 0%, #000 100%)"
        if os.path.exists("HOLA.png"):
            with open("HOLA.png", "rb") as f:
                encoded_hola = base64.b64encode(f.read()).decode('utf-8')
            hola_bg = f"linear-gradient(rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.5)), url('data:image/png;base64,{encoded_hola}')"

        st.markdown(f"""
        <div style="height: 100%; min-height: 400px; background: {hola_bg}; background-size: cover; background-position: center; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-direction: column; border: 1px solid #333; overflow: hidden;">
            <h2 style="color: #fff; letter-spacing: 5px; text-transform: uppercase; margin-bottom: 5px; text-shadow: 2px 2px 6px rgba(0,0,0,0.8);">Data Behind</h2>
            <h2 style="color: #D32F2F; letter-spacing: 5px; text-transform: uppercase; margin-top: 0px; text-shadow: 2px 2px 6px rgba(0,0,0,0.8);">Great Stories</h2>
        </div>
        """, unsafe_allow_html=True)

elif page == "Pending Approvals":
    st.markdown("<h2 style='margin-top: 0;'>Crisis Pivots Requiring Approval</h2>", unsafe_allow_html=True)
    actions = list(db.collection("pending_actions").where("status", "==", "pending").stream())
    
    if not actions:
        st.info("No pending approvals at this time. All campaigns are stable.")
        
    for action in actions:
        data = action.to_dict()
        st.markdown("<div class='approval-card'>", unsafe_allow_html=True)
        col_thumb, col_content, col_actions = st.columns([1, 5, 2])
        with col_thumb:
            st.markdown("""
            <div style="height: 130px; background: #222; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: 1px solid #444;">
                <span style="color: #666; font-size: 0.7rem; text-align: center;">[Poster<br>Thumb]</span>
            </div>
            """, unsafe_allow_html=True)
        with col_content:
            st.markdown(f"<h3 style='margin-top: 0; margin-bottom: 5px;'>{data.get('movie_title')}</h3>", unsafe_allow_html=True)
            st.markdown("<span style='color: #888; font-size: 0.8rem;'>Created recently</span>", unsafe_allow_html=True)
            st.write("**Pivot Plan Summary:**")
            st.write(data.get("pivot_plan"))
        with col_actions:
            st.write("")
            if st.button("Approve", key=f"app_{action.id}", type="primary", use_container_width=True):
                db.collection("pending_actions").document(action.id).update({"status": "approved"})
                st.success("Pivot Approved.")
                st.rerun()
            if st.button("Reject", key=f"rej_{action.id}", use_container_width=True):
                db.collection("pending_actions").document(action.id).update({"status": "rejected"})
                st.warning("Pivot Rejected.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

else:
    # DASHBOARD
    col_dash_head, col_dash_action = st.columns([3, 1])
    with col_dash_head:
        st.markdown("<h2 style='margin-top: 0; margin-bottom: 0;'>Campaign Sentiment</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color: #aaa; margin-top: 0;'>Track real-time PR impact and audience shifts</p>", unsafe_allow_html=True)
    
    campaigns = list(db.collection("campaigns").stream())
    
    if not campaigns:
        st.info("No active campaigns available.")
    else:
        with col_dash_action:
            selected_campaign = st.selectbox("Select Campaign", options=[c.id for c in campaigns], format_func=lambda x: [c.to_dict().get("movie_title") for c in campaigns if c.id == x][0], label_visibility="collapsed")
            if st.button("Run Agent Now", type="primary", use_container_width=True):
                import requests
                try:
                    requests.post("http://localhost:8000/trigger-monitor")
                    st.success("Agent triggered! Please wait ~45 seconds and refresh.")
                except Exception as e:
                    st.error(f"Failed to trigger agent: {e}")

        st.write("")
        history_docs = list(db.collection("campaigns").document(selected_campaign).collection("history").order_by("timestamp").stream())
        campaign_doc = [c.to_dict() for c in campaigns if c.id == selected_campaign][0]
        
        if not history_docs:
            st.info("No monitoring history yet. The agent is either running or waiting for the schedule.")
        else:
            records = []
            for doc in history_docs:
                d = doc.to_dict()
                report = d.get("report", {})
                records.append({
                    "Timestamp": d.get("timestamp"),
                    "Overall Score": report.get("sentiment_score", 50),
                    "Critic Score": report.get("critic_sentiment_score", 50),
                    "Audience Score": report.get("audience_sentiment_score", 50),
                    "Is Crisis": d.get("is_crisis", False)
                })
            df = pd.DataFrame(records)
            
            # --- Chart & Poster Split ---
            col_chart, col_poster = st.columns([3.5, 1])
            with col_chart:
                fig = px.line(df, x="Timestamp", y=["Overall Score", "Critic Score", "Audience Score"], 
                              markers=True, 
                              color_discrete_sequence=["#2196F3", "#4CAF50", "#F44336"])
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)", 
                    font_color="#e0e0e0",
                    margin=dict(l=0, r=0, t=30, b=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                fig.add_hline(y=25, line_dash="dash", line_color="#D32F2F", annotation_text="Crisis Floor (25)", annotation_font_color="#D32F2F")
                st.plotly_chart(fig, use_container_width=True)
                
            with col_poster:
                st.write("")
                
            # --- Detail / Report View ---
            st.markdown("<hr style='border-color: #333;'>", unsafe_allow_html=True)
            col_det1, col_det2 = st.columns([1, 5])
            with col_det1:
                st.markdown("""
                <div style="height: 160px; background: #222; border-radius: 6px; display: flex; align-items: center; justify-content: center; border: 1px solid #444;">
                    <span style="color: #666; font-size: 0.7rem; text-align: center;">[Poster Thumb]</span>
                </div>
                """, unsafe_allow_html=True)
            with col_det2:
                status_text = campaign_doc.get('status', 'ACTIVE').upper()
                st.markdown(f"<h3 style='margin-bottom: 5px; margin-top: 0;'>{campaign_doc.get('movie_title')} <span style='background-color: #2e7d32; padding: 4px 10px; border-radius: 12px; font-size: 0.6rem; vertical-align: middle; margin-left: 10px; letter-spacing: 1px;'>{status_text}</span></h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #888; font-size: 0.9rem;'><strong>Cast:</strong> {', '.join(campaign_doc.get('cast', []))}</p>", unsafe_allow_html=True)
                
                latest_report = history_docs[-1].to_dict().get("report", {})
                conf = latest_report.get("confidence", "unknown").upper()
                conf_color = "#F44336" if conf == "LOW" else "#FF9800" if conf == "MEDIUM" else "#4CAF50"
                st.markdown(f"<p style='font-size: 0.9rem;'><strong>Confidence:</strong> <span style='color: {conf_color}; font-weight: bold;'>{conf}</span></p>", unsafe_allow_html=True)
            
            st.write("")
            tab1, tab2 = st.tabs(["Overview", "Reports & Grounding"])
            with tab1:
                st.markdown("**Executive Summary:**")
                st.write(latest_report.get("summary", ""))
                st.write("")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Key Narratives**")
                    for n in latest_report.get("key_narratives", []): st.write(f"- {n}")
                with c2:
                    st.markdown("**Controversies Detected**")
                    for c in latest_report.get("controversies_detected", []): st.write(f"- {c}")
            with tab2:
                st.markdown("**Queries Used by Agent:**")
                for q in latest_report.get("search_queries_used", []): st.write(f"- {q}")
                st.write("")
                st.markdown("**Source Links:**")
                for s in latest_report.get("sources", []): st.write(f"🔗 {s}")
