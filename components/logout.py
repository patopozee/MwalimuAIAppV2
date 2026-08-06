import streamlit as st
from services.session_service import destroy_session


def render():

    @st.dialog("🚪 Log Out")
    def confirm_logout():

        st.info(
            "You are about to sign out.\n\n"
            "Your learning progress has already been saved."
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

        with col2:
            if st.button(
                "🚪 Log Out",
                type="primary",
                use_container_width=True
            ):
                destroy_session()
                st.rerun()

    st.sidebar.markdown("---")

    with st.sidebar.container(border=True):

        st.markdown("### 🚪 Sign Out")

        if st.button(
            "Log Out",
            use_container_width=True
        ):
            confirm_logout()