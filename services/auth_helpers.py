from datetime import datetime, timezone
from typing import Any
from firebase_admin import firestore

db = firestore.client()


def normalize_grade(grade_value: Any) -> str:
    """
    Normalizes any grade input (e.g., '6', 'grade 6', 'Grade 6 ') into 
    the standard 'Grade X' key required by the curriculum engine.
    """
    if not grade_value:
        return "Grade 6"

    clean_str = str(grade_value).strip().title()

    # Convert numeric inputs like "6" -> "Grade 6"
    if clean_str.isdigit():
        return f"Grade {clean_str}"

    # If it's already properly prefixed, e.g. "Grade 6"
    if clean_str.startswith("Grade"):
        return clean_str

    return "Grade 6"


def get_or_create_user_profile(uid: str, email: str, name: str) -> dict[str, Any]:
    """
    Retrieves an existing Firestore user profile or initializes a new one.
    Guarantees strict 'grade' formatting to prevent downstream LMS errors.
    """
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()

    if doc.exists:
        existing = doc.to_dict()

        if existing is not None:
            # Fix existing profiles that might have a missing, blank, or improperly formatted grade
            current_grade = existing.get("grade")
            formatted_grade = normalize_grade(current_grade)

            if current_grade != formatted_grade:
                existing["grade"] = formatted_grade
                doc_ref.update({"grade": formatted_grade})

            return existing

    # Create new profile defaults for OAuth or direct signups
    profile = {
        "uid": uid,
        "name": name.strip().title(),
        "email": email.lower().strip(),
        "grade": "Grade 6",
        "age": 12,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "subscription": {
            "tier": "Free",
            "payment_status": "Pending",
            "reference_id": "",
            "expiry_date": ""
        }
    }

    doc_ref.set(profile)

    return profile