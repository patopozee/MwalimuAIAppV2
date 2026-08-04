import streamlit as st

def render():

    st.sidebar.markdown("### Navigation Hub")
    st.sidebar.page_link(
        st.session_state.ROUTE_CHAT,
        use_container_width=True,
    )

    st.sidebar.page_link(
        st.session_state.ROUTE_VOICE,
        use_container_width=True,
    )

    st.sidebar.page_link(
        st.session_state.ROUTE_GENERATORS,
        use_container_width=True,
    )

    st.sidebar.page_link(
        st.session_state.ROUTE_LEARNING,
        use_container_width=True,
    )

    st.sidebar.page_link(
        st.session_state.ROUTE_LEADERBOARD,
        use_container_width=True,
    )