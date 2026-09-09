import os
import uuid
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from google.cloud import firestore
from agent.orchestrator import run_orchestrator
from tools.notifier import send_approval_email

app = FastAPI()
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "cast-506804")
db = firestore.Client(project=PROJECT_ID)

class CampaignCreate(BaseModel):
    movie_title: str
    cast: list[str] = []

@app.post("/campaigns")
def create_campaign(campaign: CampaignCreate):
    campaign_id = str(uuid.uuid4())
    db.collection("campaigns").document(campaign_id).set({
        "movie_title": campaign.movie_title,
        "cast": campaign.cast,
        "status": "active",
        "last_run_status": "idle",
        "created_at": firestore.SERVER_TIMESTAMP
    })
    return {"id": campaign_id}

@app.post("/trigger-monitor")
def trigger_monitor(background_tasks: BackgroundTasks):
    background_tasks.add_task(process_campaigns)
    return {"status": "triggered"}

def process_campaigns():
    campaigns = db.collection("campaigns").where("status", "==", "active").stream()
    for doc in campaigns:
        c = doc.to_dict()
        cid = doc.id
        if c.get("last_run_status") == "in_progress": continue
        db.collection("campaigns").document(cid).update({"last_run_status": "in_progress"})
        try:
            state_docs = list(db.collection("campaigns").document(cid).collection("history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1).stream())
            previous_state = state_docs[0].to_dict().get("report") if state_docs else None
            result = run_orchestrator(c.get("movie_title", ""), c.get("cast", []), previous_state)
            
            db.collection("campaigns").document(cid).collection("history").add({
                "timestamp": firestore.SERVER_TIMESTAMP,
                "report": result["report"],
                "is_crisis": result["is_crisis"]
            })
            if result["is_crisis"]:
                pid = str(uuid.uuid4())
                pivot = result["report"].get("recommended_pivot", "N/A")
                db.collection("pending_actions").document(pid).set({
                    "movie_id": cid, "movie_title": c.get("movie_title"), "pivot_plan": pivot, "status": "pending"
                })
                send_approval_email(c.get("movie_title"), pid, pivot, "http://localhost:8501")
                
            db.collection("campaigns").document(cid).update({"last_run_status": "success", "last_error": firestore.DELETE_FIELD})
        except Exception as e:
            db.collection("campaigns").document(cid).update({"last_run_status": "error", "last_error": str(e)})
