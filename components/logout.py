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
                # Using a native programmatic script restart to close the modal layout cleanly
                st.rerun()

        with col2:
            if st.button(
                "🚪 Log Out",
                type="primary",
                use_container_width=True
            ):
                # 1. Purge active persistence states securely 
                destroy_session()
                
                # 2. ✅ FIX: Reset tracking properties to guarantee the user lands back on the login view
                st.session_state.user_authenticated = False
                st.session_state.current_page = "Main Chat"
                
                # 3. Force full app lifecycle redraw execution
                st.rerun()

    st.sidebar.markdown("---")

    with st.sidebar.container(border=True):
        st.markdown("### :material/logout: Sign Out")
        if st.button("Log Out", use_container_width=True):
            confirm_logout()
