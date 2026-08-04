import streamlit as st


def load():

    sidebar_open = st.session_state.get("sidebar_open", True)

    left_offset = "320px" if sidebar_open else "60px"

    st.markdown(f"""
    <style>

    /* Hide Streamlit header background only */
    header[data-testid="stHeader"]{{
        background:transparent !important;
        border:none !important;
        box-shadow:none !important;
    }}

    /* Main container */

    .mw-header{{
        position:fixed;

        top:0;

        left:{left_offset};

        right:0;

        height:72px;

        display:flex;

        justify-content:space-between;

        align-items:center;

        padding:10px 20px;

        z-index:9999;

        transition:left .25s ease;
    }}

    /* Shared card style */

    .mw-brand-card,
    .mw-context-card,
    .mw-profile,
    .mw-icon{{
        background:#1F2937;

        border:1px solid #2E394D;

        border-radius:16px;

        box-sizing:border-box;
    }}

    /* ========================= */

    .mw-brand-card{{
        display:flex;

        align-items:center;

        gap:14px;

        height:52px;

        padding:0 18px;
    }}

    .mw-logo{{
        width:38px;
        height:38px;
    }}

    .mw-brand-text{{
        display:flex;
        flex-direction:column;
    }}   

    .mw-title{{
        color:white;
        font-size:18px;
        font-weight:700;
    }}

    .mw-subtitle{{
        color:#94A3B8;
        font-size:11px;
    }}

    /* ========================= */

    .mw-context-card{{
        display:flex;

        align-items:center;

        gap:10px;

        height:52px;

        padding:0 20px;

        color:#E5E7EB;

        font-size:13px;
    }}

    /* ========================= */

    .mw-right{{
        display:flex;

        align-items:center;

        gap:12px;
    }}

    /* ========================= */

    .mw-icon{{
        width:44px;

        height:44px;

        display:flex;

        justify-content:center;

        align-items:center;

        cursor:pointer;

        font-size:17px;

        color:white;

        transition:.2s;
    }}

    .mw-icon:hover{{
        background:#2563EB;
    }}

    /* ========================= */

    .mw-plan{{
        background:#FACC15;

        color:black;

        border-radius:12px;

        padding:8px 14px;

        font-size:11px;

        font-weight:700;
    }}

    /* ========================= */

    .mw-profile{{
        display:flex;

        align-items:center;

        gap:10px;

        height:52px;

        padding:0 16px;
    }}

    .mw-avatar{{
        width:34px;

        height:34px;

        border-radius:50%;

        background:#2563EB;

        display:flex;

        align-items:center;

        justify-content:center;

        color:white;

        font-weight:700;
    }}

    .mw-name{{
        color:white;

        font-size:14px;

        font-weight:600;
    }}

    /* Push page below header */

    div[data-testid="stMainBlockContainer"]{{
        padding-top:82px !important;
    }}

    </style>
    """, unsafe_allow_html=True)