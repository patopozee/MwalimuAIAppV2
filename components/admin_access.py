#components/admin_access.py
import streamlit as st
from services.navigation_service import navigate_to
from services.database import delete_leaderboard_table

MASTER_ADMIN_UIDS = [
    "aYiSGN6DVbOLuM3jYnQSEGpd8Mo2",
    "dwnwZWdjDhhWRLVm02LGp6D3L7u2",
]

# 1. Define the confirmation dialog function
@st.dialog("Confirm Database Deletion")
def confirm_wipe_dialog():
    st.warning("⚠️ Warning: This will permanently drop the leaderboard table and delete all ranking records. This action cannot be undone.")
    st.write("Are you absolutely sure you want to proceed?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Wipe Table", type="primary", use_container_width=True):
            try:
                delete_leaderboard_table()
                st.success("Leaderboard table dropped successfully!")
                st.rerun()  # Refresh the UI to reflect changes
            except Exception as e:
                st.error(f"Error: {e}")
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()  # Close the dialog safely

def render():
    uid = st.session_state.get("uid")
    if uid not in MASTER_ADMIN_UIDS:
        return
        
    if st.sidebar.button(
        " Admin Dashboard",
        key="admin_dashboard_btn",
        use_container_width=True,
    ):
        navigate_to(
            st.session_state.ROUTE_ADMIN,
            "Admin Dashboard",
            "admin",
        )
        
    # Admin database destruction portal
    st.sidebar.markdown("---")
    st.sidebar.subheader("Danger Zone")
    
    # 2. Trigger the modal dialog on click instead of executing directly
    if st.sidebar.button("🚨 Wipe Leaderboard Table", key="wipe_lb_btn", use_container_width=True):
        confirm_wipe_dialog()
