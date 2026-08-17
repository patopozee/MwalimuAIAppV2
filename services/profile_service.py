import streamlit as st

# -----------------------------
# Get current profile
# -----------------------------
def get_student_profile() -> dict:
    profile = st.session_state.get("user_profile")

    if not isinstance(profile, dict):
        profile = {}

    return profile


# -----------------------------
# Update current profile
# -----------------------------
def set_student_profile(profile: dict):
    if not isinstance(profile, dict):
        profile = {}

    raw_grade = profile.get("grade", "Grade 6")
    raw_grade_str = str(raw_grade).strip().title()
    
    # Standardize grade string formatting to "Grade X"
    if raw_grade_str.isdigit():
        formatted_grade = f"Grade {raw_grade_str}"
    elif raw_grade_str.startswith("Grade"):
        formatted_grade = raw_grade_str
    else:
        formatted_grade = "Grade 6"

    # Clean profile fields
    clean_name = str(profile.get("name", "Student")).strip().title() or "Student"
    clean_email = str(profile.get("email", "")).strip().lower()
    
    try:
        clean_age = int(profile.get("age", 12))
    except (ValueError, TypeError):
        clean_age = 12

    # Update inner dictionary so get_student_grade() matches session_state
    profile["name"] = clean_name
    profile["grade"] = formatted_grade
    profile["age"] = clean_age
    profile["email"] = clean_email

    # Sync Streamlit Session States
    st.session_state.user_profile = profile
    st.session_state.student_name = clean_name
    st.session_state.grade = formatted_grade
    st.session_state.age = clean_age
    st.session_state.user_email = clean_email


# -----------------------------
# Convenience getters
# -----------------------------
def get_student_name() -> str:
    return st.session_state.get("student_name") or get_student_profile().get("name", "Student")


def get_student_grade() -> str:
    return st.session_state.get("grade") or get_student_profile().get("grade", "Grade 6")


def get_student_age() -> int:
    try:
        return int(st.session_state.get("age") or get_student_profile().get("age", 12))
    except (ValueError, TypeError):
        return 12


def get_student_email() -> str:
    return st.session_state.get("user_email") or get_student_profile().get("email", "")