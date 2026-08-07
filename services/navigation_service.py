import streamlit as st
from services.session_service import update_session


def navigate_to(page, page_name, active_view="main"):

    # Update local workspace
    st.session_state.current_page = page_name
    st.session_state.active_view = active_view

    # Persist destination to Firebase
    try:
        update_session()
    except Exception as e:
        print(f"Navigation workspace save failed: {e}")

    # Navigate
    st.switch_page(page)