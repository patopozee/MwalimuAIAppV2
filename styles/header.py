import streamlit as st


def load():

    sidebar_open = st.session_state.get("sidebar_open", True)

    left_offset = "320px" if sidebar_open else "60px"

    st.markdown(
        f"""
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

    /* ===========================================================
   MOBILE (Phones & Small Tablets)
    =========================================================== */

    @media (max-width: 768px){{

        .mw-header{{

            left:0 !important;

            right:0 !important;

            height:auto;

            padding:10px;

            flex-direction:column;

            align-items:stretch;

            gap:10px;

        }}

        /* Brand */

        .mw-brand-card{{

            width:100%;

            height:auto;

            padding:10px 14px;

        }}

        .mw-logo{{

            width:32px;

            height:32px;

        }}

        .mw-title{{

            font-size:16px;

        }}

        .mw-subtitle{{

            font-size:10px;

        }}

        /* Subject card */

        .mw-context-card{{

            width:100%;

            justify-content:center;

            flex-wrap:wrap;

            height:auto;

            padding:10px;

            gap:6px;

            font-size:11px;

        }}

        /* Right section */

        .mw-right{{

            width:100%;

            justify-content:space-between;

            gap:8px;

        }}

        .mw-icon{{

            width:38px;

            height:38px;

            font-size:15px;

        }}

        .mw-plan{{

            padding:6px 10px;

            font-size:10px;

        }}

        .mw-profile{{

            flex:1;

            justify-content:center;

            height:44px;

            padding:0 10px;

        }}

        .mw-avatar{{

            width:28px;

            height:28px;

            font-size:12px;

        }}

        .mw-name{{

            font-size:12px;

        }}

        /* Push Streamlit page down enough */

        div[data-testid="stMainBlockContainer"]{{

            padding-top:180px !important;

        }}

    }}

    </style>
    """,
        unsafe_allow_html=True,
    )