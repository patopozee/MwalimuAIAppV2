import streamlit as st
from services.navigation_service import navigate_to

def render_quick_actions():
    st.sidebar.markdown("### :material/bolt: Quick Actions")

    # --- VOICE TUTOR ACTION ---
    if st.sidebar.button(
        label="Practice Speaking With Voice Tutor",
        icon=":material/mic:",  # 🎙️ -> Native Material Mic
        key="voice_btn",
        use_container_width=True,
    ):
        navigate_to(
            st.session_state.ROUTE_VOICE,
            "Voice Tutor",
            "voice",
        )

    # --- LEARNING DASHBOARD ACTION ---
    if st.sidebar.button(
        label="Certificates/Learning Dashboard",
        icon=":material/menu_book:",  # 📚 -> Native Material Book
        key="learning_btn",
        use_container_width=True,
    ):
        navigate_to(
            st.session_state.ROUTE_LEARNING,
            "Learning Dashboard",
            "learning",
        )
