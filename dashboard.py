import os
import streamlit as st
import pandas as pd
import plotly.express as px
from google.cloud import firestore
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Agentic Cinema | PR Orchestrator", layout="wide")

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

def login():
    st.title("Studio Executive Portal")
    st.info("Requires a Firebase account with an 'executive' role in Firestore.")
    
    email = st.text_input("Email")
    pwd = st.text_input("Password", type="password")
    
    if st.button("Login"):
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
        st.rerun()

if st.session_state["role"] != "executive":
    login()
    st.stop()

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Register Campaign", "Pending Approvals"])

if page == "Register Campaign":
    st.header("Register New Film Campaign")
    with st.form("campaign_form"):
        title = st.text_input("Movie Title")
        cast = st.text_input("Cast (comma-separated)")
        submitted = st.form_submit_button("Start Monitoring")
        if submitted and title:
            db.collection("campaigns").add({
                "movie_title": title,
                "cast": [c.strip() for c in cast.split(",") if c.strip()],
                "status": "active",
                "last_run_status": "idle",
                "created_at": firestore.SERVER_TIMESTAMP
            })
            st.success(f"Campaign '{title}' registered successfully!")

elif page == "Pending Approvals":
    st.header("Crisis Pivots Requiring Executive Approval")
    actions = list(db.collection("pending_actions").where("status", "==", "pending").stream())
    if not actions:
        st.info("No pending approvals.")
    for action in actions:
        data = action.to_dict()
        with st.expander(f"Pivot Required: {data.get('movie_title')}"):
            st.write("**Recommended Pivot Plan:**")
            st.write(data.get("pivot_plan"))
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Approve & Execute", key=f"app_{action.id}"):
                    db.collection("pending_actions").document(action.id).update({"status": "approved"})
                    st.success("Pivot Approved.")
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"rej_{action.id}"):
                    db.collection("pending_actions").document(action.id).update({"status": "rejected"})
                    st.warning("Pivot Rejected.")
                    st.rerun()

else:
    st.header("Campaign Sentiment Dashboard")
    campaigns = list(db.collection("campaigns").stream())
    
    if not campaigns:
        st.info("No active campaigns.")
    else:
        selected_campaign = st.selectbox("Select Campaign", options=[c.id for c in campaigns], format_func=lambda x: [c.to_dict().get("movie_title") for c in campaigns if c.id == x][0])
        
        # Load History
        history_docs = list(db.collection("campaigns").document(selected_campaign).collection("history").order_by("timestamp").stream())
        
        if not history_docs:
            st.info("No monitoring history yet. The agent is either running or waiting for the schedule.")
            if st.button("Run Agent Now"):
                import requests
                try:
                    requests.post("http://localhost:8000/trigger-monitor")
                    st.success("Agent triggered! Please wait ~45 seconds and refresh.")
                except Exception as e:
                    st.error(f"Failed to trigger agent: {e}")
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
            
            # Plot Sentiment Over Time
            fig = px.line(df, x="Timestamp", y=["Overall Score", "Critic Score", "Audience Score"], markers=True, title="Sentiment Tracking")
            # Draw crisis floor line
            fig.add_hline(y=25, line_dash="dash", line_color="red", annotation_text="Crisis Floor (25)")
            st.plotly_chart(fig, use_container_width=True)
            
            # Show latest report details
            latest_report = history_docs[-1].to_dict().get("report", {})
            st.subheader("Latest Assessment")
            st.write(latest_report.get("summary", ""))
            
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Key Narratives**")
                for n in latest_report.get("key_narratives", []): st.write(f"- {n}")
            with col2:
                st.write("**Controversies Detected**")
                for c in latest_report.get("controversies_detected", []): st.write(f"- {c}")
                
            with st.expander("Sources & Grounding Queries"):
                st.write("**Queries Used by Agent:**")
                st.write(latest_report.get("search_queries_used", []))
                st.write("**Source Links:**")
                for s in latest_report.get("sources", []):
                    st.write(f"🔗 {s}")
