# styles/sidebar.py
import streamlit as st


def load():
    st.markdown(
        """
    <style>
    section[data-testid="stSidebar"] {
        background: #1A1D24 !important;
        z-index: 999995 !important;
        transition: transform 0.3s ease, margin-left 0.3s ease, left 0.3s ease !important;
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
    is_open = st.session_state.get("sidebar_open", True)
    
    # Desktop positioning vs Mobile off-screen force (-100vw ensures 100% off-screen hiding)
    sidebar_left = "0px" if is_open else "-100vw"

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
        
        /* Desktop specific limit to prevent full viewport shift */
        @media (min-width: 769px) {{
            section[data-testid="stSidebar"] {{
                left: {'0px' if is_open else '-340px'} !important;
            }}
        }}

        /* Force complete hide on mobile screens when closed */
        @media (max-width: 768px) {{
            section[data-testid="stSidebar"][aria-expanded="false"],
            section[data-testid="stSidebar"] {{
                left: {sidebar_left} !important;
                max-width: 85vw !important; /* Prevents sidebar from taking 100% device width on small phones */
            }}
        }}
        
        /* Adjust core workspace bounds */
        [data-testid="stApp"] {{
            margin-left: 0px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )