import streamlit as st
from config import CBC
from services.database import get_ask_mwalimu_history


def render():
    st.sidebar.markdown("---")
    st.sidebar.subheader(":material/menu_book: Learning Context")

    # Fetch global grade metadata configuration bounds from context
    grade = st.session_state.get("grade", "Grade 6")
    grade_dict = CBC.get(grade, {})

    if not isinstance(grade_dict, dict):
        grade_dict = {}

    # -------------------------------------------------------------
    # 1. SUBJECT CONFIGURATION LAYER
    # -------------------------------------------------------------
    subjects = list(grade_dict.keys()) or ["General Studies"]
    
    # Read or initialize the master selected subject tracking point
    if "active_subject" not in st.session_state:
        st.session_state.active_subject = subjects[0]

    saved_subject = st.session_state.active_subject
    sub_idx = subjects.index(saved_subject) if saved_subject in subjects else 0

    subject = st.sidebar.selectbox(
        "Subject",
        options=subjects,
        index=sub_idx,
        key="master_subject_selector_widget",
    )

    # 🚨 TRIGGER RESET: If the user clicked a new subject, wipe child selections instantly
    if subject != st.session_state.active_subject:
        st.session_state.active_subject = subject
        st.session_state.pop("active_topic", None)
        st.session_state.pop("active_sub_topic", None)
        st.session_state.pop("active_learning_outcome", None)
        st.session_state.pop("active_curriculum", None)
        st.cache_data.clear()
        st.rerun()

    subject_dict = grade_dict.get(subject, {})
    if not isinstance(subject_dict, dict):
        subject_dict = {}

    # -------------------------------------------------------------
    # 2. TOPIC CONFIGURATION LAYER (Dynamic Key Fixed)
    # -------------------------------------------------------------
    topics = list(subject_dict.keys()) or ["General Topic"]
    
    if "active_topic" not in st.session_state or st.session_state.active_topic not in topics:
        st.session_state.active_topic = topics[0]

    saved_topic = st.session_state.active_topic
    top_idx = topics.index(saved_topic) if saved_topic in topics else 0

    # 🚀 DYNAMIC KEY: Changing the subject changes this key, forcing a complete widget reset
    topic = st.sidebar.selectbox(
        "Topic",
        options=topics,
        index=top_idx,
        key=f"topic_select_dynamic_{subject}", 
    )

    if topic != st.session_state.active_topic:
        st.session_state.active_topic = topic
        st.session_state.pop("active_sub_topic", None)
        st.session_state.pop("active_learning_outcome", None)
        st.rerun()

    topic_dict = subject_dict.get(topic, {})

    # -------------------------------------------------------------
    # 3. SUB-TOPIC CONFIGURATION LAYER (Dynamic Key Fixed)
    # -------------------------------------------------------------
    if isinstance(topic_dict, dict):
        sub_topics = list(topic_dict.keys()) or ["General Sub-Topic"]
    else:
        sub_topics = ["General Sub-Topic"]

    if "active_sub_topic" not in st.session_state or st.session_state.active_sub_topic not in sub_topics:
        st.session_state.active_sub_topic = sub_topics[0]

    saved_subtopic = st.session_state.active_sub_topic
    subtop_idx = sub_topics.index(saved_subtopic) if saved_subtopic in sub_topics else 0

    # 🚀 DYNAMIC KEY: Resets when topic changes
    sub_topic = st.sidebar.selectbox(
        "Sub-topic",
        options=sub_topics,
        index=subtop_idx,
        key=f"subtopic_select_dynamic_{subject}_{topic}",
    )

    if sub_topic != st.session_state.active_sub_topic:
        st.session_state.active_sub_topic = sub_topic
        st.session_state.pop("active_learning_outcome", None)
        st.rerun()

    # Gather matching outcomes
    if isinstance(topic_dict, dict):
        raw_outcomes = topic_dict.get(sub_topic, [])
    else:
        raw_outcomes = topic_dict

    if isinstance(raw_outcomes, dict):
        outcomes = list(raw_outcomes.keys()) or ["General Learning Outcome"]
    elif isinstance(raw_outcomes, list):
        outcomes = [str(o) for o in raw_outcomes] if raw_outcomes else ["General Learning Outcome"]
    else:
        outcomes = [str(raw_outcomes)] if raw_outcomes else ["General Learning Outcome"]

    # -------------------------------------------------------------
    # 4. LEARNING OUTCOME CONFIGURATION LAYER (Dynamic Key Fixed)
    # -------------------------------------------------------------
    if "active_learning_outcome" not in st.session_state or st.session_state.active_learning_outcome not in outcomes:
        st.session_state.active_learning_outcome = outcomes[0]

    saved_outcome = st.session_state.active_learning_outcome
    out_idx = outcomes.index(saved_outcome) if saved_outcome in outcomes else 0

    # 🚀 DYNAMIC KEY: Resets when sub-topic changes
    learning_outcome = st.sidebar.selectbox(
        "Learning Outcome",
        options=outcomes,
        index=out_idx,
        key=f"outcome_select_dynamic_{subject}_{topic}_{sub_topic}",
    )

    if learning_outcome != st.session_state.active_learning_outcome:
        st.session_state.active_learning_outcome = learning_outcome
        st.rerun()

    # -------------------------------------------------------------
    # 5. SYNCHRONIZE UNIFIED CURRICULUM STATE OBJECT MAP
    # -------------------------------------------------------------
    st.session_state.active_curriculum = {
        "subject": subject,
        "topic": topic,
        "sub_topic": sub_topic,
        "learning_outcome": learning_outcome,
    }

    # ============================================================
    # 6. BACKEND DATABASE HISTORY LOOKUP SYNC LAYER
    # ============================================================
    student_uid = str(st.session_state.get("uid", ""))
    student_name = st.session_state.get("student_name", "")

    if student_uid and student_name:
        current_subject = st.session_state.active_subject

        if st.session_state.get("last_checked_subject") != current_subject:
            all_history = get_ask_mwalimu_history(
                student_uid,
                current_subject
            )

            st.session_state.ask_mwalimu_history = [
                msg for msg in all_history
                if not msg.get("is_voice")
            ]

            st.session_state.last_checked_subject = current_subject
