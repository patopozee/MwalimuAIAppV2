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

        left:0;

        width:0;

        height:72px;

        display:flex;

        justify-content:space-between;

        align-items:center;

        padding:10px 20px;

        z-index:99999;

        transition:
            left .25s ease,
            width .25s ease;

        box-sizing:border-box;
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
    
            gap:10px;
    
            height:52px;
    
            padding:0 20px;
    
            color:#E5E7EB;
    
            font-size:10px;
    }}

    .mw-logo{{
        width:44px;
        height:44px;
    }}

    .mw-brand-text{{
        display:flex;
        flex-direction:column;
    }}   

    .mw-title{{
        color:white;
        font-size:12px;
        font-weight:700;
    }}

    .mw-subtitle{{
        color:#94A3B8;
        font-size:8px;
    }}

    /* ========================= */

    .mw-context-card{{
        display:flex;

        align-items:center;

        gap:10px;

        height:52px;

        padding:0 20px;

        color:#E5E7EB;

        font-size:10px;
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

        font-size:14px;

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
        width:40px;

        height:40px;

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

        font-weight:400;
    }}

    /* Push page below header */

    div[data-testid="stMainBlockContainer"]{{
        padding-top:82px !important;
    }}
    
   /* ===========================================================
   MOBILE (Phones & Small Tablets ONLY)
   =========================================================== */
   @media (max-width: 768px){{

       .mw-header{{
           position: fixed !important;
           top: 4px !important;
           left: 4px !important;
           right: 4px !important;
           width: auto !important;
           height: auto !important;
           display: flex !important;
           flex-direction: column !important;
           align-items: stretch !important;
           gap: 2px !important;
           padding: 4px 8px !important;
           background: rgba(17, 24, 39, 0.95) !important;
           backdrop-filter: blur(8px) !important;
           border: 1px solid #2E394D !important;
           border-radius: 12px !important;
           box-sizing: border-box !important;
           z-index: 99999 !important;
           transition: none !important;
       }}

       /* Top Row: Brand Header */
       .mw-brand-card{{
           width: 100% !important;
           height: 26px !important;
           padding: 0 4px !important;
           background: transparent !important;
           border: none !important;
           gap: 6px !important;
       }}

       .mw-logo{{
           width: 22px !important;
           height: 22px !important;
       }}

       .mw-title{{
           font-size: 11px !important;
           line-height: 1 !important;
       }}

       .mw-subtitle{{
           display: block !important;
           font-size: 7.5px !important;
           color: #94A3B8 !important;
           line-height: 1 !important;
           margin-top: 1px !important;
       }}

       /* Middle Row: Context Breadcrumbs */
       .mw-context-card {{
           display: flex !important;
           width: 100% !important;
           justify-content: center !important;
           align-items: center !important;
           font-size: 8.5px !important;
           padding: 1px 0 !important;
           background: transparent !important;
           border: none !important;
           opacity: 0.85;
           white-space: nowrap !important;
           overflow-x: auto !important;
       }}

       /* Bottom Row: Icons & User Profile */
       .mw-right{{
           width: 100% !important;
           display: flex !important;
           justify-content: space-between !important;
           align-items: center !important;
           gap: 4px !important;
           padding-top: 2px !important;
       }}

       .mw-icon{{
           width: 28px !important;
           height: 28px !important;
           font-size: 11px !important;
           border-radius: 8px !important;
       }}

       .mw-plan{{
           padding: 3px 8px !important;
           font-size: 9.5px !important;
           border-radius: 6px !important;
       }}

       .mw-profile{{
           height: 28px !important;
           padding: 0 6px !important;
           gap: 4px !important;
           border-radius: 8px !important;
       }}

       .mw-avatar{{
           width: 20px !important;
           height: 20px !important;
           font-size: 9px !important;
       }}

       .mw-name{{
           font-size: 10px !important;
       }}

       /* Push main page layout smoothly below compact mobile card */
       div[data-testid="stMainBlockContainer"]{{
           padding-top: 115px !important;
       }}
   }}

    </style>
    """,
        unsafe_allow_html=True,
    )
    st.iframe("""
    <script>

    function updateHeader(){

        const sidebar =
            window.parent.document.querySelector(
                'section[data-testid="stSidebar"]'
            );

        const header =
            window.parent.document.querySelector(".mw-header");

        const main =
            window.parent.document.querySelector(
                '[data-testid="stMainBlockContainer"]'
            );

        if(!sidebar || !header || !main) return;

        const rect = main.getBoundingClientRect();

        header.style.left = rect.left + "px";
        header.style.width = rect.width + "px";

    }

    updateHeader();

    const resizeObserver =
        new ResizeObserver(updateHeader);

    resizeObserver.observe(
        window.parent.document.querySelector(
            'section[data-testid="stSidebar"]'
        )
    );

    window.parent.addEventListener(
        "resize",
        updateHeader
    );

    setInterval(updateHeader,300);

    </script>
    """, height=1)