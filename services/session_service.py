import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

import streamlit as st
from services.firebase_init import db

SESSION_COLLECTION = "sessions"
COOKIE_NAME = "mwalimu_session"

COOKIE_SECRET = st.secrets.get(
    "cookie_secret",
    "fallback_local_secret_key_2026"
).encode()


# =====================================================
# Cookie helpers
# =====================================================

def _sign_token(token: str) -> str:
    signature = hmac.new(
        COOKIE_SECRET,
        token.encode(),
        hashlib.sha256
    ).digest()

    payload = {
        "token": base64.urlsafe_b64encode(token.encode()).decode(),
        "signature": base64.urlsafe_b64encode(signature).decode()
    }

    return base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode()


def _verify_token(value: str):
    try:
        payload = json.loads(
            base64.urlsafe_b64decode(value.encode()).decode()
        )

        token = base64.urlsafe_b64decode(
            payload["token"].encode()
        ).decode()

        received = base64.urlsafe_b64decode(
            payload["signature"].encode()
        )

        expected = hmac.new(
            COOKIE_SECRET,
            token.encode(),
            hashlib.sha256
        ).digest()

        if hmac.compare_digest(received, expected):
            return token

    except Exception:
        pass

    return None


def get_token_from_browser():

    headers = st.context.headers
    cookie_header = headers.get("Cookie", "")

    cookies = {}

    for item in cookie_header.split(";"):
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()

    raw = cookies.get(COOKIE_NAME)

    if not raw:
        return None

    return _verify_token(raw)


# =====================================================
# Session manager
# =====================================================

def create_session(uid: str, email: str):

    session_id = secrets.token_urlsafe(64)

    db.collection(SESSION_COLLECTION).document(session_id).set({

        "uid": uid,
        "email": email,

        "workspace": {
            "current_page": "Main Chat",
            "active_view": "main"
        },

        "created_at": datetime.now(timezone.utc),

        "expires": datetime.now(timezone.utc)
        + timedelta(days=30)

    })

    st.session_state.session_id = session_id

    cookie = _sign_token(session_id)

    st.html(f"""
    <script>
    document.cookie =
    "{COOKIE_NAME}={cookie};
    path=/;
    max-age=2592000;
    SameSite=Lax";
    </script>
    """)

    return session_id


def validate_session():

    session_id = get_token_from_browser()

    if not session_id:
        return None

    doc = db.collection(
        SESSION_COLLECTION
    ).document(session_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()

    if not data:
        return None

    expires = data.get("expires")

    if expires is None:
        return None

    if expires.tzinfo is None:
        expires = expires.replace(
            tzinfo=timezone.utc
        )

    if datetime.now(timezone.utc) > expires:

        try:
            db.collection(
                SESSION_COLLECTION
            ).document(session_id).delete()
        except Exception:
            pass

        return None

    st.session_state.session_id = session_id

    return data


def update_session():

    session_id = st.session_state.get("session_id")

    if not session_id:
        return

    workspace = {
        "current_page": st.session_state.get(
            "current_page",
            "Main Chat"
        ),
        "active_view": st.session_state.get(
            "active_view",
            "main"
        ),

        # Future additions
        "selected_subject": st.session_state.get(
            "selected_subject"
        ),
        "selected_topic": st.session_state.get(
            "selected_topic"
        ),
        "selected_generator": st.session_state.get(
            "selected_generator"
        ),
        "lesson_id": st.session_state.get(
            "lesson_id"
        ),
    }

    db.collection(SESSION_COLLECTION).document(session_id).update({
        "workspace": workspace,
        "last_seen": datetime.now(timezone.utc)
    })


def destroy_session():

    session_id = st.session_state.get("session_id")

    if session_id:
        try:
            db.collection(SESSION_COLLECTION).document(session_id).delete()
        except Exception:
            pass

    # Remove browser cookie
    st.html(f"""
    <script>
        document.cookie =
        "{COOKIE_NAME}=;
        path=/;
        expires=Thu, 01 Jan 1970 00:00:00 GMT";
    </script>
    """)

    # Completely clear Streamlit session
    st.session_state.clear()

    # Recreate default values needed after logout
    st.session_state.user_authenticated = False
    st.session_state.session_checked = False