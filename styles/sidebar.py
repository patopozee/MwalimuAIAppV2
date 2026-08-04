# styles/sidebar.py
import streamlit as st


def load():
    st.markdown(
        """
    <style>
    section[data-testid="stSidebar"] {
        background: #1A1D24 !important;
        z-index: 999995 !important;
        transition: transform 0.3s ease, margin-left 0.3s ease !important;
    }

    .sidebar-section-title {
        color: #94A3B8; font-size: 12px; font-weight: 700; letter-spacing: .8px;
        text-transform: uppercase; margin-top: 10px; margin-bottom: 10px;
    }

    section[data-testid="stSidebar"] button {
        border-radius: 12px !important; height: 48px !important;
        font-size: 15px !important; font-weight: 600 !important; transition: .2s;
    }
    section[data-testid="stSidebar"] button:hover { transform: translateX(4px); }

    section[data-testid="stSidebar"] a {
        border-radius: 12px !important; margin-bottom: 8px !important;
        padding: 10px 12px !important; transition: .25s; font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] a:hover { background: #2563eb22 !important; transform: translateX(4px); }
    section[data-testid="stSidebar"] a[aria-current="page"] {
        background: #2563eb33 !important; border-left: 4px solid #3b82f6 !important; color: white !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def load_style():
    # Detect position states
    sidebar_left = "0px" if st.session_state.get("sidebar_open", True) else "-340px"

    st.markdown(
        f"""
        <style>
        /* Smooth position layout tracking adjustments */
        section[data-testid="stSidebar"] {{
            left: {sidebar_left} !important;
            transition: left .25s ease-in-out !important;
            width: 320px !important;
            z-index: 999995 !important;
        }}
        
        div[data-testid="stSidebarContent"] {{
            width: 320px !important;
        }}
        
        /* Adjust core workspace bounds to flex dynamically alongside the side drawer layer */
        [data-testid="stApp"] {{
            margin-left: {'0px' if not st.session_state.get('sidebar_open', True) else '0px'} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
