import streamlit as st

PAGES = [
    ("🏠", "Main Chat"),
    ("🎙️", "Voice Tutor"),
    ("⚡", "Generators Hub"),
    ("🏫", "Learning Dashboard"),
    ("🏆", "Leaderboard Hub"),
]



def navigate(page_name: str):
    """
    Navigate to a page and synchronize it with the browser URL.
    """
    st.session_state.current_page = page_name

    st.query_params["page"] = page_name

    st.rerun()