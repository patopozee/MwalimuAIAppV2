import streamlit as st

from services.database import (
    get_student_stats,
    get_student_learning_analysis,
    get_student_quiz_history,
    get_student_data,
)

from services.db_service import MwalimuDBService
from services.tier_guard import TIER_LIMITS, is_subscription_active


@st.fragment
def render():

    name = str(st.session_state.get("student_name") or "").strip()

    if not name:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📈 Progress Dashboard")
        st.sidebar.caption("Fill in your name to start tracking progress.")
        return

    grade = st.session_state.get("grade", "Grade 1")
    age = int(st.session_state.get("age", 10))
    uid = str(st.session_state.get("uid", ""))

    # ==========================================================
    # Progress Dashboard
    # ==========================================================

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Progress Dashboard")

    stats = get_student_stats(uid, grade, age)

    st.sidebar.metric("Quizzes Taken", stats["quizzes"])
    st.sidebar.metric(
        "Average Score",
        f"{stats.get('average_score',0)}%"
    )

    analysis = get_student_learning_analysis(
        uid,
        grade,
        age,
    )

    st.sidebar.markdown(
        f"**Learning Status:** `{analysis.get('current_level','Medium')}`"
    )

    # 📊 Clean, collapsible topics to save space
    if analysis.get("weak_topics"):
        with st.sidebar.expander("❌ Needs Improvement", expanded=False):
            for topic in analysis["weak_topics"]:
                st.caption(f"{topic}")

    if analysis.get("strong_topics"):
        with st.sidebar.expander("✅ Mastered Areas", expanded=False):
            for topic in analysis["strong_topics"]:
                st.caption(f"{topic}")

    history = get_student_quiz_history(uid, grade, age)

    if history:
        st.sidebar.markdown("**Performance Trend**")
        st.sidebar.line_chart(history)

    # ==========================================================
    # Daily Limits
    # ==========================================================

    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Daily Generation Limits")

    # Always retrieve fresh student data to prevent stale session caching
    uid = str(st.session_state.get("uid", "")).strip()

    if not uid:
        st.sidebar.error("User ID missing. Please sign in again.")
        return

    profile = get_student_data(uid) or {}

    subscription = profile.get("subscription", {})
    raw_tier = str(subscription.get("tier", "Free")).strip().lower()

    # Verify if subscription is active first
    tier_is_active = is_subscription_active(profile)

    if tier_is_active and "premium" in raw_tier:
        tier_key = "Premium"
    elif tier_is_active and "plus" in raw_tier:
        tier_key = "Mwalimu AI Plus"
    else:
        tier_key = "Free"

    limits = TIER_LIMITS.get(
        tier_key,
        TIER_LIMITS["Free"],
    )

    def usage(key):

        used = MwalimuDBService.get_daily_usage(uid, key)
        limit = limits.get(key, 1)

        if limit == float("inf"):
            return f"{used} / ∞"

        remaining = max(0, limit - used)

        return f"{used} / {limit}"

    st.sidebar.markdown(f"💬 **Ask Mwalimu:** `{usage('questions')}`")
    st.sidebar.markdown(f"📅 **Study Plans:** `{usage('has_study_plan')}`")
    st.sidebar.markdown(f"📝 **Quizzes:** `{usage('quizzes')}`")
    st.sidebar.markdown(f"🎴 **Flashcards:** `{usage('flashcards')}`")
    st.sidebar.markdown(f"📚 **Lessons:** `{usage('lessons')}`")
    st.sidebar.markdown(f"📤 **Uploads:** `{usage('has_upload')}`")
