# firebase_auth.py — minimal shim (no real login; always "Guest")
def login_user() -> str:
    return "Guest"
