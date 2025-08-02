import firebase_admin
from firebase_admin import credentials, firestore
import json
import streamlit as st

# Load Firebase credentials from Streamlit secrets
firebase_config = st.secrets["firebase"]
# Initialize Firebase app if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)


db = firestore.client()

def log_user_activity(username, action):
    db.collection("user_logs").add({
        "username": username,
        "action": action
    })

def save_project(username, project_name, data):
    # ✅ Automatically wrap lists so Firestore accepts them
    if isinstance(data, list):
        data = {"data": data}
    db.collection("projects").document(username).collection("user_projects").document(project_name).set(data)

def load_project_data(username, project_name):
    doc = db.collection("projects").document(username).collection("user_projects").document(project_name).get()
    if doc.exists:
        return doc.to_dict()
    else:
        return None
