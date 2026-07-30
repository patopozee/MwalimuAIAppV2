from datetime import datetime
from typing import Any
from firebase_admin import firestore

db = firestore.client()

def get_or_create_user_profile(uid, email, name) -> dict[str, Any]:

    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()

    if doc.exists:
        existing = doc.to_dict()

        if existing is not None:
            return existing

    profile = {
        "uid": uid,
        "name": name,
        "email": email.lower().strip(),
        "grade": "Grade 6",
        "age": 12,
        "created_at": datetime.utcnow().isoformat(),
        "subscription": {
            "tier": "Free",
            "payment_status": "Pending",
            "reference_id": "",
            "expiry_date": ""
        }
    }

    doc_ref.set(profile)

    return profile