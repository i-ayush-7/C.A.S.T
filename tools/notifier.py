import os
import requests

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
TO_EMAIL = os.getenv("ALERT_EMAIL_ADDRESS")

def send_approval_email(movie_title: str, pid: str, pivot: str, dashboard_url: str):
    if not RESEND_API_KEY or not TO_EMAIL:
        print(f"Missing RESEND_API_KEY or ALERT_EMAIL_ADDRESS. Mocking email for {movie_title}.")
        return

    subject = f"🚨 URGENT: PR Crisis Detected for '{movie_title}'"
    
    html_content = f"""
    <h2>Crisis Pivot Recommended for {movie_title}</h2>
    <h3>Recommended Action:</h3>
    <p>{pivot}</p>
    <br>
    <a href="{dashboard_url}" style="padding: 10px 20px; background-color: #d9534f; color: white; text-decoration: none; border-radius: 5px;">Review in Executive Dashboard</a>
    <p style="font-size: 12px; color: gray;">Action ID: {pid}</p>
    """
    
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": "onboarding@resend.dev",
        "to": TO_EMAIL,
        "subject": subject,
        "html": html_content
    }
    
    response = requests.post("https://api.resend.com/emails", headers=headers, json=payload)
    if response.status_code in (200, 201):
        print(f"Successfully sent Resend email alert to {TO_EMAIL} for {movie_title}")
    else:
        print(f"Failed to send email. Status: {response.status_code}, Error: {response.text}")
