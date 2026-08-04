
import streamlit as st
from config import CBC
from services.database import get_ask_mwalimu_history


def render():

    st.sidebar.markdown("---")
    st.sidebar.subheader("📚 Learning Context")

    grade = st.session_state.get("grade", "Grade 6")

    grade_dict = CBC.get(grade, {})

    if not isinstance(grade_dict, dict):
        grade_dict = {}

    # -----------------------------
    # SUBJECT
    # -----------------------------
    subjects = list(grade_dict.keys()) or ["General Studies"]

    subject = st.sidebar.selectbox(
        "Subject",
        subjects,
        key="sidebar_subject_select",
    )

    subject_dict = grade_dict.get(subject, {})

    if not isinstance(subject_dict, dict):
        subject_dict = {}

    # -----------------------------
    # TOPIC
    # -----------------------------
    topics = list(subject_dict.keys()) or ["General Topic"]

    topic = st.sidebar.selectbox(
        "Topic",
        topics,
        key="sidebar_topic_select",
    )

    topic_dict = subject_dict.get(topic, {})

    # -----------------------------
    # SUB TOPIC
    # -----------------------------
    if isinstance(topic_dict, dict):

        sub_topics = list(topic_dict.keys()) or ["General Sub-Topic"]

        sub_topic = st.sidebar.selectbox(
            "Sub-topic",
            sub_topics,
            key="sidebar_subtopic_select",
        )

        outcomes = topic_dict.get(sub_topic, [])

    else:

        sub_topic = "General Sub-Topic"
        outcomes = topic_dict

    if not outcomes:
        outcomes = ["General Learning Outcome"]

    # -----------------------------
    # LEARNING OUTCOME
    # -----------------------------
    learning_outcome = st.sidebar.selectbox(
        "Learning Outcome",
        outcomes,
        key="sidebar_outcome_select",
    )

    # -----------------------------
    # Detect changes
    # -----------------------------
    current = {
        "subject": subject,
        "topic": topic,
        "sub_topic": sub_topic,
        "learning_outcome": learning_outcome,
    }

    previous = st.session_state.get("active_curriculum")

    if previous != current:

        st.session_state.active_curriculum = current

        st.session_state.active_subject = subject
        st.session_state.active_topic = topic
        st.session_state.active_sub_topic = sub_topic
        st.session_state.active_learning_outcome = learning_outcome

        st.rerun()
    # ============================================================
    # LOAD SUBJECT CHAT HISTORY
    # ============================================================

    student_uid = str(st.session_state.get("uid", ""))
    student_name = st.session_state.get("student_name", "")

    if student_uid and student_name:

        current_subject = st.session_state.active_subject

        if (
            st.session_state.get("last_checked_subject") != current_subject
        ):

            all_history = get_ask_mwalimu_history(
                student_uid,
                current_subject
            )

            st.session_state.ask_mwalimu_history = [
                msg for msg in all_history
                if not msg.get("is_voice")
            ]

            st.session_state.last_checked_subject = current_subject