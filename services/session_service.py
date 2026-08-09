#services/session_service.py
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
import urllib.parse

import streamlit as st
from streamlit_cookies_controller import CookieController
from services.firebase_init import db

# Configuration
SESSION_COLLECTION = "sessions"
COOKIE_NAME = "mwalimu_session"
COOKIE_SECRET = st.secrets.get("cookie_secret", "fallback_local_secret_key_2026").encode()


# =====================================================
# Cookie Cryptography Helpers
# =====================================================

def _sign_token(token: str) -> str:
    """Signs and encodes the token into a single verifiable base64 string."""
    signature = hmac.new(COOKIE_SECRET, token.encode(), hashlib.sha256).digest()
    
    payload = {
        "token": base64.urlsafe_b64encode(token.encode()).decode(),
        "signature": base64.urlsafe_b64encode(signature).decode()
    }
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

def _verify_token(signed_value: str) -> str | None:
    """Decodes the signed cookie value and verifies its signature integrity."""
    try:
        decoded_payload = json.loads(base64.urlsafe_b64decode(signed_value.encode()).decode())
        token = base64.urlsafe_b64decode(decoded_payload["token"].encode()).decode()
        received_signature = base64.urlsafe_b64decode(decoded_payload["signature"].encode())
        
        expected_signature = hmac.new(COOKIE_SECRET, token.encode(), hashlib.sha256).digest()
        
        if hmac.compare_digest(expected_signature, received_signature):
            return token
    except Exception:
        pass
    return None

def get_token_from_browser() -> str | None:
    """Reads raw cookies scoped ONLY to the current active user context."""
    # 1. ALWAYS check native st.context first (instant, headers-based, no frame lag)
    try:
        if hasattr(st, "context") and hasattr(st.context, "cookies"):
            raw_cookie = st.context.cookies.get(COOKIE_NAME)
            if raw_cookie:
                clean_cookie = urllib.parse.unquote(raw_cookie).strip('"')
                verified = _verify_token(clean_cookie)
                if verified:
                    return verified
    except Exception:
        pass

    # 2. Fallback to component controller if header check is unavailable
    try:
        user_controller = CookieController()
        raw_cookie = user_controller.get(COOKIE_NAME)
        if raw_cookie:
            clean_cookie = urllib.parse.unquote(str(raw_cookie)).strip('"')
            verified = _verify_token(clean_cookie)
            if verified:
                return verified
    except Exception:
        pass
    return None


# =====================================================
# State & Database Session Managers
# =====================================================

def create_session(uid: str, email: str) -> str:
    """Generates a unique workspace session for an individual user browser."""
    session_id = secrets.token_urlsafe(64)

    db.collection(SESSION_COLLECTION).document(session_id).set({
        "uid": uid,
        "email": email,
        "workspace": {
            "current_page": "Main Chat",
            "active_view": "main"
        },
        "created_at": datetime.now(timezone.utc),
        "expires": datetime.now(timezone.utc) + timedelta(days=30)
    })

    st.session_state.session_id = session_id
    cookie = _sign_token(session_id)

    user_controller = CookieController()
    user_controller.set(
        COOKIE_NAME, 
        cookie, 
        max_age=2592000, 
        path="/"
    )
    return session_id

def validate_session() -> dict | None:
    """Validates the current unique user session."""
    session_id = get_token_from_browser()

    if not session_id:
        return None

    doc = db.collection(SESSION_COLLECTION).document(session_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    if not data:
        return None

    expires = data.get("expires")
    if expires is None:
        return None

    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        try:
            db.collection(SESSION_COLLECTION).document(session_id).delete()
        except Exception:
            pass
        return None

    st.session_state.session_id = session_id
    return data

def update_session() -> None:
    """Saves app UI selections for this specific user session down to Firebase."""
    session_id = st.session_state.get("session_id")
    if not session_id:
        return

    workspace = {
        "current_page": st.session_state.get("current_page", "Main Chat"),
        "active_view": st.session_state.get("active_view", "main"),
        "selected_subject": st.session_state.get("selected_subject"),
        "selected_topic": st.session_state.get("selected_topic"),
        "selected_generator": st.session_state.get("selected_generator"),
        "lesson_id": st.session_state.get("lesson_id"),
    }

    db.collection(SESSION_COLLECTION).document(session_id).update({
        "workspace": workspace,
        "last_seen": datetime.now(timezone.utc)
    })

def destroy_session() -> None:
    """Wipes active trace records ONLY for the user clicking log out."""
    session_id = st.session_state.get("session_id")

    if session_id:
        try:
            db.collection(SESSION_COLLECTION).document(session_id).delete()
        except Exception:
            pass

    try:
        user_controller = CookieController()
        if hasattr(user_controller, "_CookieController__cookies"):
            user_controller.remove(COOKIE_NAME, path="/")
        else:
            try:
                user_controller.remove(COOKIE_NAME, path="/")
            except KeyError:
                pass
    except Exception:
        pass

    # 1. Completely clear local execution state arrays
    st.session_state.clear()
    
    # 2. Hardcode authentication parameters off
    st.session_state.user_authenticated = False
    st.session_state.session_checked = True
    
    # 3. ✅ FORCE COMPLETE APP-LEVEL REDRAW LIFECYCLE
    # This acts as an immediate reset break that drops the interface onto the login landing page!
    st.rerun()

