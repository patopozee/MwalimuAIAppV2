import secrets
from datetime import datetime, timedelta, timezone

import extra_streamlit_components as stx
from services.firebase_init import db

SESSION_COLLECTION = "sessions"

# One global cookie manager
cookie_manager = stx.CookieManager()


def create_session(uid, email):
    session_id = secrets.token_urlsafe(64)

    db.collection(SESSION_COLLECTION).document(session_id).set({
        "uid": uid,
        "email": email,
        "expires": datetime.now(timezone.utc) + timedelta(days=30)
    })

    cookie_manager.set(
        "mwalimu_session",
        session_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )

    return session_id


def validate_session():
    session_id = cookie_manager.get("mwalimu_session")

    if not session_id:
        return None

    doc = db.collection(SESSION_COLLECTION).document(session_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()

    if data is None:
        return None

    expires = data.get("expires")

    if expires is None:
        destroy_session()
        return None

    # Normalize timezone
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires:
        destroy_session()
        return None

    return data


def destroy_session():
    session_id = cookie_manager.get("mwalimu_session")

    if session_id:
        db.collection(SESSION_COLLECTION).document(session_id).delete()

    cookie_manager.delete("mwalimu_session")