import streamlit as st


def navigate_to(page, page_name, active_view="main"):
    """
    Intentional in-app navigation.

    Persist the destination page, then navigate to it.
    """

    st.session_state.current_page = page_name
    st.session_state.active_view = active_view

    try:
        from services.session_service import update_session
        update_session()
    except Exception as e:
        print(f"Navigation workspace save failed: {e}")

    st.switch_page(page)