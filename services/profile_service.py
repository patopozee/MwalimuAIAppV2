import streamlit as st


# -----------------------------
# Get current profile
# -----------------------------
def get_student_profile():
    profile = st.session_state.get("user_profile")

    if profile is None:
        profile = {}

    return profile


# -----------------------------
# Update current profile
# -----------------------------
def set_student_profile(profile: dict):
    st.session_state.user_profile = profile

    st.session_state.student_name = profile.get("name", "Student")
    st.session_state.grade = profile.get("grade", "Grade 1")
    st.session_state.age = int(profile.get("age", 10))
    st.session_state.user_email = profile.get("email", "")


# -----------------------------
# Convenience getters
# -----------------------------
def get_student_name():
    return get_student_profile().get("name", "Student")


def get_student_grade():
    return get_student_profile().get("grade", "Grade 1")


def get_student_age():
    return int(get_student_profile().get("age", 10))


def get_student_email():
    return get_student_profile().get("email", "")