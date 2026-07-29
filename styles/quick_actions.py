import streamlit as st


def render_quick_actions():

    st.sidebar.markdown("### ⚡ Quick Actions")

    if st.sidebar.button(
        "🎙 Voice Tutor\nPractice speaking with AI",
        key="voice_btn",
        use_container_width=True,
    ):
        st.switch_page(st.session_state.ROUTE_VOICE)

    if st.sidebar.button(
        "🏫 Learning Dashboard\n,View lessons & certificates",
        key="learning_btn",
        use_container_width=True,
    ):
        st.switch_page(st.session_state.ROUTE_LEARNING)

    if st.sidebar.button(
        "⚙ Edit Profile\n/Manage your student profile",
        
        key="profile_btn",
        use_container_width=True,
    ):
        st.switch_page(st.session_state.ROUTE_EDIT_PROFILE)