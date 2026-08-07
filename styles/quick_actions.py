import streamlit as st
from services.navigation_service import navigate_to


def render_quick_actions():

    st.sidebar.markdown("### ⚡ Quick Actions")

    if st.sidebar.button(
        "🎙️ Voice Tutor\nPractice speaking with AI",
        key="voice_btn",
        use_container_width=True,
    ):
        navigate_to(
            st.session_state.ROUTE_VOICE,
            "Voice Tutor",
            "voice",
        )

    if st.sidebar.button(
        "📚 Learning Dashboard\nView lessons & certificates",
        key="learning_btn",
        use_container_width=True,
    ):
        navigate_to(
            st.session_state.ROUTE_LEARNING,
            "Learning Dashboard",
            "learning",
        )