import streamlit as st


def load():
    sidebar_open = st.session_state.get("sidebar_open", True)
    banner_left = "320px" if sidebar_open else "60px"

    st.markdown(
        f"""
    <style>
    /* 1. Fully reset native header container */
    header[data-testid="stHeader"] {{
        background:transparent !important;
        box-shadow:none !important;
        border:none !important;
    }}

    /* 2. TARGET COLLAPSED STATE CONTROL CONTAINER (Fixes high button when closed) */
    div[data-testid="stSidebarCollapsedControl"] {{
        position: fixed !important;
        top: 16px !important;            /* Vertical alignment inside header */
        left: 14px !important;
        z-index: 1000000 !important;
        pointer-events: auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 36px !important;
        width: 36px !important;
    }}

    /* Target inner button inside collapsed container */
    div[data-testid="stSidebarCollapsedControl"] button {{
        position: relative !important;
        top: 0 !important;
        left: 0 !important;
        color: #ffffff !important;
        background: transparent !important;
        border: none !important;
        width: 100% !important;
        height: 100% !important;
    }}

    /* 3. TARGET EXPANDED STATE SIDEBAR BUTTON */
    button[data-testid="stSidebarCollapseButton"],
    button[aria-label="Close sidebar"] {{
        position: fixed !important;
        top: 16px !important;
        left: 14px !important;
        z-index: 1000000 !important;
        color: #ffffff !important;
        background: transparent !important;
        pointer-events: auto !important;
        height: 36px !important;
        width: 36px !important;
    }}

    /* Hover effects for both button states */
    div[data-testid="stSidebarCollapsedControl"]:hover,
    button[data-testid="stSidebarCollapseButton"]:hover {{
        background: rgba(255, 255, 255, 0.12) !important;
        border-radius: 8px !important;
    }}

    /* 4. TRANSPARENT HEADER WRAPPER */
    .mwalimu-header-wrapper {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 68px;
        z-index: 99990;
        background: transparent !important;
        pointer-events: none;
        font-family: Inter, sans-serif;
    }}

    /* 5. VISIBLE HEADER BANNER */
    .hdr-banner {{
       position:absolute;

    top:0;

    right:0;

    left:{banner_left};

    height:68px;

    background:transparent !important;

    border:none !important;

    box-shadow:none !important;

    backdrop-filter:none !important;

    display:flex;

    justify-content:space-between;

    align-items:center;

    padding:0 24px;

    transition:left .25s ease-in-out;

    pointer-events:auto;
    }}

    .hdr-left {{ display:flex;
        align-items:center;
        gap:14px;

        height:52px;

        padding:0 18px;

        border-radius:16px;

        background:#1f2937;

        border:1px solid #2f3747; }}
    .hdr-logo {{ width: 40px; height: 40px; }}
    .hdr-title {{ display:flex; flex-direction:column; justify-content:center; }}
    .hdr-title h2 {{  margin:0 color:white; font-size:18px; font-weight:700; line-height:0; }}
    .hdr-title span {{color:#94A3B8; font-size:11px; line-height:1.1; }}

    .hdr-center {{
        display:flex;
        align-items:center;
        gap:10px;

        height:52px;

        padding:0 20px;

        border-radius:16px;

        background:#1f2937;

        border:1px solid #2f3747;

        color:#E5E7EB;

        font-size:13px;

        font-weight:500;
    }}

    .hdr-right {{ display:flex; align-items:center; gap:12px; }}
    .hdr-icon {{
         width:44px;

        height:44px;

        display:flex;

        align-items:center;

        justify-content:center;

        border-radius:14px;

        background:#1f2937;

        border:1px solid #2f3747;

        color:white;

        font-size:17px;

        transition:.2s;
    }}
    .hdr-icon:hover {{ background:#2563eb; }}
    .hdr-premium {{ display:flex;

        align-items:center;

        justify-content:center;

        height:36px;

        padding:0 14px;

        border-radius:12px;

        background:#facc15;

        color:black;

        font-size:11px;

        font-weight:700; }}
    .hdr-profile {{ 

            display:flex;

            align-items:center;

            gap:10px;

            height:52px;

            padding:0 16px;

            border-radius:16px;

            background:#1f2937;

            border:1px solid #2f3747;

            }}
    .hdr-avatar {{ width:34px;

            height:34px;

            border-radius:50%;

            background:#2563eb;

            display:flex;

            align-items:center;

            justify-content:center;

            color:white;

            font-weight:700;

            font-size:14px; }}
    .hdr-name {{ color:white; font-size:14px; font-weight:600; }}

    div[data-testid="stMainBlockContainer"] {{ padding-top: 82px !important; }}
    </style>
    """,
        unsafe_allow_html=True,
    )