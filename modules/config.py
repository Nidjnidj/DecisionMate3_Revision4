def run(T):
    import firebase_admin
    from firebase_admin import credentials, firestore
    import os
    
    # Get the absolute path to the JSON key
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    KEY_PATH = os.path.join(BASE_DIR, "serviceAccountKey.json")
    
    # Initialize Firebase app only once
    if not firebase_admin._apps:
        cred = credentials.Certificate(KEY_PATH)
        firebase_admin.initialize_app(cred)
    
    # Initialize Firestore
    db = firestore.client()

config = run
