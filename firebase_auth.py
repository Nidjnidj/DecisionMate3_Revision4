import pyrebase

# Firebase configuration (public API part for client auth)
firebase_config = {
    "apiKey": "your-api-key",
    "authDomain": "your-app.firebaseapp.com",
    "projectId": "your-app",
    "storageBucket": "your-app.appspot.com",
    "messagingSenderId": "your-sender-id",
    "appId": "your-app-id",
    "databaseURL": ""
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()


def login_user(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return user
    except Exception as e:
        return {"error": str(e)}


def signup_user(email, password):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        return user
    except Exception as e:
        return {"error": str(e)}
