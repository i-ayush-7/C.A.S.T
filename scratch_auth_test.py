import os
import requests
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()
API_KEY = os.environ.get('FIREBASE_WEB_API_KEY')
PROJECT_ID = os.environ.get('GCP_PROJECT_ID', 'cast-506804')

db = firestore.Client(project=PROJECT_ID)

users = [
    {'email': 'exec@test.com', 'password': 'password123', 'role': 'executive'},
    {'email': 'producer@test.com', 'password': 'password123', 'role': 'producer'}
]

def signup_and_set_role(u):
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}'
    r = requests.post(url, json={'email': u['email'], 'password': u['password'], 'returnSecureToken': True})
    
    if 'EMAIL_EXISTS' in r.text:
        url_in = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}'
        r = requests.post(url_in, json={'email': u['email'], 'password': u['password'], 'returnSecureToken': True})
        
    uid = r.json().get('localId')
    db.collection('users').document(uid).set({'role': u['role']})
    print(f"Setup {u['email']} -> UID: {uid}, Role: {u['role']}")

for u in users:
    signup_and_set_role(u)

print('\n--- TESTING LOGIN FLOW ---')

def simulate_login(email, pwd):
    print(f"Attempting login for: {email}")
    url = f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}'
    resp = requests.post(url, json={'email': email, 'password': pwd, 'returnSecureToken': True})
    
    if resp.status_code != 200:
        print(f"  [UI ERROR] Authentication failed: {resp.json().get('error', {}).get('message')}")
        return False
        
    uid = resp.json().get('localId')
    user_doc = db.collection('users').document(uid).get()
    
    if not user_doc.exists:
        print(f"  [UI ERROR] User document not found in Firestore. Access Denied.")
        return False
        
    role = user_doc.to_dict().get('role')
    if role != 'executive':
        print(f"  [UI ERROR] Governance Check Failed: Your role is '{role}'. Executives only.")
        return False
        
    print(f"  [UI SUCCESS] Login successful! Role: {role}. Approve/Reject controls unlocked.")
    return True

simulate_login('exec@test.com', 'password123')
simulate_login('producer@test.com', 'password123')
