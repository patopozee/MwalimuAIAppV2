# services/ui_layout.py
import streamlit as st
from services.db_service import MwalimuDBService
from services.ui_components import show_upgrade_modal

def render_workspace_sidebar(uid):
    """
    Renders the workspace sidebar independently.
    Pass 'uid' as an argument to avoid undefined variable errors.
    """
    with st.sidebar:
        st.header("Workspace")
        
        # Add your profile logic here...
        
        st.markdown("---")
        if st.button("Upgrade to Premium"):
            st.session_state.show_upgrade_modal = True
            st.rerun()
            
        # Add other sidebar navigation or stats here