import streamlit as st

MASTER_ADMIN_UIDS = [
    "aYiSGN6DVbOLuM3jYnQSEGpd8Mo2",
    "dwnwZWdjDhhWRLVm02LGp6D3L7u2",
]


def render():

    if st.session_state.get("uid") not in MASTER_ADMIN_UIDS:
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("👑 Administrative Access")

    st.sidebar.page_link(
        st.session_state.ROUTE_ADMIN,
        label="⚙️ Open Admin Dashboard",
        icon="👑",
        use_container_width=True,
    )