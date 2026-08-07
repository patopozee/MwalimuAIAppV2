import streamlit as st
from services.navigation_service import navigate_to

MASTER_ADMIN_UIDS = [
    "aYiSGN6DVbOLuM3jYnQSEGpd8Mo2",
    "dwnwZWdjDhhWRLVm02LGp6D3L7u2",
]


def render():
    uid = st.session_state.get("uid")

    if uid not in MASTER_ADMIN_UIDS:
        return

    if st.sidebar.button(
        "👑 Admin Dashboard",
        key="admin_dashboard_btn",
        use_container_width=True,
    ):
        navigate_to(
            st.session_state.ROUTE_ADMIN,
            "Admin Dashboard",
            "admin",
        )