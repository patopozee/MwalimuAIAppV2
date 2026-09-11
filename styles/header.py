import streamlit as st


import streamlit as st


import streamlit as st


def load():
    st.markdown(
        """
    <style>
    /* Hide default Streamlit header bar background */
    header[data-testid="stHeader"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        z-index: 9999 !important;
    }

    /* Desktop Outer Header Shell (800px max width centered) */
    @media (min-width: 769px) {
        .mw-header {
            position: fixed !important;
            top: 10px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: min(800px, calc(100vw - 40px)) !important;
            height: 52px !important;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            z-index: 99999 !important;
            box-sizing: border-box !important;
            transition: left 0.25s ease, width 0.25s ease !important;
        }

        /* Shift header dynamically when desktop sidebar expands */
        body:has(section[data-testid="stSidebar"][aria-expanded="true"]) .mw-header {
            left: calc(50% + 160px) !important;
            width: min(800px, calc(100vw - 360px)) !important;
        }
    }

    /* Shared card styles */
    .mw-brand-card,
    .mw-context-card,
    .mw-profile,
    .mw-icon {
        background: #1F2937;
        border: 1px solid #2E394D;
        border-radius: 16px;
        box-sizing: border-box;
    }

    /* Desktop Brand Card */
    .mw-brand-card {
        display: flex;
        align-items: center;
        gap: 8px;
        height: 52px;
        padding: 0 16px;
        color: #E5E7EB;
    }

    .mw-logo {
        width: 32px;
        height: 32px;
    }

    .mw-brand-text {
        display: flex;
        flex-direction: column;
    }   

    .mw-title {
        color: white;
        font-size: 12px;
        font-weight: 700;
    }

    .mw-subtitle {
        color: #94A3B8;
        font-size: 8px;
    }

    /* Desktop Context Card */
    .mw-context-card {
        display: flex;
        align-items: center;
        gap: 6px;
        height: 52px;
        padding: 0 16px;
        color: #E5E7EB;
        font-size: 11px;
    }

    /* Desktop Right Section */
    .mw-right {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .mw-icon {
        width: 44px;
        height: 44px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        font-size: 14px;
        color: white;
        transition: 0.2s;
    }

    .mw-icon:hover {
        background: #2563EB;
    }

    .mw-plan {
        background: #FACC15;
        color: black;
        border-radius: 12px;
        padding: 8px 14px;
        font-size: 11px;
        font-weight: 700;
    }

    .mw-profile {
        display: flex;
        align-items: center;
        gap: 10px;
        height: 52px;
        padding: 0 16px;
    }

    .mw-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #2563EB;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
    }

    .mw-name {
        color: white;
        font-size: 13px;
    }

    div[data-testid="stMainBlockContainer"] {
        padding-top: 80px !important;
    }

    /* ===========================================================
       MOBILE (Phones & Small Tablets ONLY)
    =========================================================== */
    @media (max-width: 768px) {
    div[data-testid="stSidebarCollapsedControl"],
    button[aria-label="Open sidebar"] {
        z-index: 100001 !important;
        position: fixed !important;
        top: 6px !important;
        left: 6px !important;
        background: #1F2937 !important;
        border: 1px solid #2E394D !important;
        border-radius: 6px !important;
        color: #FFFFFF !important;
    }

    /* Entire outer header box (Symmetrical Margins) */
    .mw-header {
        position: fixed !important;
        top: 4px !important;
        left: 44px !important;            /* Left margin offset to clear the » toggle button */
        right: 44px !important;            /* Matching right margin for balance */
        width: auto !important;
        height: auto !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        gap: 1px !important;
        padding: 4px 8px !important;
        background: rgba(17, 24, 39, 0.95) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid #2E394D !important;
        border-radius: 10px !important;
        box-sizing: border-box !important;
        z-index: 99999 !important;
        transition: none !important;
    }

        /* Top Row Layout (Brand Left, Profile/Icons Right) */
        .mw-header-top {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* Brand Card (Logo + Text) */
        .mw-brand-card{
            width: auto !important;
            height: auto !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            gap: 5px !important;
            margin: 0 !important;
        }

        .mw-logo{
            width: 24px !important;
            height: 24px !important;
        }

        .mw-title{
            font-size: 12px !important;
            line-height: 1 !important;
            margin: 0 !important;
        }

        .mw-subtitle{
            display: block !important;
            font-size: 7px !important;
            color: #94A3B8 !important;
            line-height: 1 !important;
            margin-top: 1.5px !important;
        }

        /* Middle/Bottom Row: Grade & Subject Breadcrumbs */
        .mw-context-card {
            display: flex !important;
            width: 100% !important;
            justify-content: center !important;
            align-items: center !important;
            font-size: 10px !important;
            padding: 0 !important;
            margin: 0 !important;
            background: transparent !important;
            border: none !important;
            opacity: 0.85;
            white-space: nowrap !important;
            overflow-x: auto !important;
            height: auto !important;
        }

        /* Right Section (Icons & Profile Pill) */
        .mw-right{
            width: auto !important;
            display: flex !important;
            justify-content: flex-end !important;
            align-items: center !important;
            gap: 3px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .mw-icon{
            width: 22px !important;
            height: 22px !important;
            font-size: 10px !important;
            border-radius: 5px !important;
            padding: 0 !important;
        }

        .mw-plan{
            padding: 2px 5px !important;
            font-size: 10px !important;
            border-radius: 4px !important;
            line-height: 1 !important;
        }

        .mw-profile{
            height: 22px !important;
            padding: 0 4px !important;
            gap: 3px !important;
            border-radius: 5px !important;
            background: #1F2937 !important;
        }

        .mw-avatar{
            width: 16px !important;
            height: 16px !important;
            font-size: 10px !important;
        }

        .mw-name{
            font-size: 10px !important;
            line-height: 1 !important;
        }

        /* Reduces top margin of chat so content sits close under the new ultra-thin header */
        div[data-testid="stMainBlockContainer"]{
            padding-top: 72px !important;
        }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )