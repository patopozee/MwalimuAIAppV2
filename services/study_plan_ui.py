import streamlit as st
from services.ai import generate_study_plan
from services.database import get_student_data, get_student_stats
from services.tier_guard import verify_tier_allowance
from services.db_service import MwalimuDBService
from services.ui_components import show_upgrade_modal


def render_study_plan_section(uid):

    st.markdown("---")
    st.subheader("AI Personalized Study Plan")

    if "study_plan_denied" not in st.session_state:
        st.session_state.study_plan_denied = False

    user_data = get_student_data(uid)

    if not user_data:
        st.warning("No student profile found.")
        return

    s_name = user_data.get("name", "Student")
    s_grade = user_data.get("grade", "Grade 1")
    s_age = user_data.get("age", 10)
    s_tier = user_data.get("tier", "Free")

    # -------------------------
    # Generate button
    # -------------------------

    if st.button(
        "Generate Today's Study Plan",
        key="gen_plan_btn",
        use_container_width=True
    ):

        if verify_tier_allowance(uid, s_tier, "has_study_plan"):

            with st.spinner("Creating your personalized study plan..."):

                stats = get_student_stats(
                    s_name,
                    s_grade,
                    int(s_age)
                )

                st.session_state.study_plan = generate_study_plan(
                    s_name,
                    stats
                )

                MwalimuDBService.increment_usage(
                    uid,
                    "has_study_plan"
                )

                # Reset denial state if they now successfully generated it
                st.session_state.study_plan_denied = False
                st.rerun()

        else:
            st.session_state.study_plan_denied = True
            st.rerun()

    # -------------------------
    # Show upgrade section
    # -------------------------

    if st.session_state.study_plan_denied:

        st.error(
            "⚠️ AI Study Plans are only available for Plus and Premium members."
        )

        if st.button(
            "🚀 Upgrade to Premium",
            key="study_plan_upgrade_unique_btn"  # Explicit unique key
        ):
            # 1. Clear the denial state flag so the error block disappears
            st.session_state.pop("study_plan_denied", None)
            
            # 2. Stage the modal to open on the next fresh frame
            st.session_state.trigger_study_upgrade_modal = True
            st.rerun()

    # -------------------------
    # Modal Activation Layer
    # -------------------------
    if st.session_state.get("trigger_study_upgrade_modal"):
        st.session_state.pop("trigger_study_upgrade_modal", None)
        show_upgrade_modal()

    # -------------------------
    # Display study plan
    # -------------------------

    if st.session_state.get("study_plan"):

        st.info(
            "Tip: Follow the allocated time intervals for maximum focus today!"
        )

        st.markdown(st.session_state.study_plan)

        if st.button(
            "Clear Study Plan",
            key="clear_plan_btn"
        ):
            st.session_state.study_plan = None
            st.rerun()
