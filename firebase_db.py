import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st

firebase_config = st.secrets["firebase"]

# Проверка и инициализация Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(firebase_config))
    firebase_admin.initialize_app(cred)

db = firestore.client()

def log_user_activity(username, action):
    db.collection("user_logs").add({
        "username": username,
        "action": action
    })

def save_project(username, project_name, data):
    if isinstance(data, list):
        data = {"data": data}
    db.collection("projects").document(username).collection("user_projects").document(project_name).set(data)

def load_project_data(username, project_name):
    doc = db.collection("projects").document(username).collection("user_projects").document(project_name).get()
    return doc.to_dict() if doc.exists else None

def load_all_projects(collection_name):
    """Load all documents in a top-level collection (e.g., process_simulations)."""
    docs = db.collection(collection_name).stream()
    return {doc.id: doc.to_dict() for doc in docs}
