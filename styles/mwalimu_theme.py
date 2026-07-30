import streamlit as st

def load_theme():
    st.markdown("""
    <style>

    :root{

        --bg:#0F1117;
        --panel:#1B1F2A;
        --card:#232838;

        --primary:#3B82F6;
        --primary-dark:#2563EB;
        --primary-light:#60A5FA;

        --success:#10B981;
        --warning:#F59E0B;
        --danger:#EF4444;

        --text:#F9FAFB;
        --muted:#9CA3AF;

    }

    html, body, [class*="css"]{
        font-family:Inter,sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        .profile-card{
            background:#1C2333;
            border:1px solid rgba(255,255,255,.08);
            border-radius:16px;
            padding:6px;
            margin-bottom:5px;
        }
    
        .profile-avatar{
            width:72px;
            height:72px;
            border-radius:50%;
            background:linear-gradient(135deg,#2563eb,#60a5fa);
            display:flex;
            align-items:center;
            justify-content:center;
            font-size:32px;
            margin:auto;
            color:white;
            font-weight:bold;
        }
    
        .profile-name{
            text-align:center;
            font-size:20px;
            font-weight:700;
            margin-top:1px;
        }
    
        .profile-grade{
            text-align:center;
            color:#9CA3AF;
            margin-bottom:1px;
        }
    
        </style>
        """, unsafe_allow_html=True)
     #=========================================================
    # NAVIGATION HUB
        # =========================================================
    # 🎨 NAVIGATION HUB DESIGN SYSTEM (HIGH-END MODERN THEME)
    # =========================================================
    st.markdown("""
        <style>
        /* Quick Action Buttons */

        div.stButton > button{

            width:100% !important;

            min-height:60px !important;


            color:white !important;

            border:none !important;

            border-radius:14px !important;

            padding:12px 18px !important;

            display:flex !important;

            justify-content:flex-start !important;

            align-items:center !important;

            box-shadow:
                0 6px 18px rgba(37,99,235,.35);

            transition:.25s;
        }

        /* ========================================================
        1. CORE TARGETING (Applies dark theme to the native button)
        ======================================================== */
        div.stButton > button {
            width: 100% !important;
            min-height: 52px !important;
            background-color: #101726 !important; /* Exact match to curriculum box background */
            border: 1px solid rgba(36, 115, 242, 0.12) !important; /* Extremely subtle blue border */
            border-radius: 12px !important;
            padding: 1px 1px !important;
            transition: all 0.2s ease-in-out !important;
            
            /* Flexbox fixes icon and text alignment */
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            text-align: left !important;
        }

        /* ========================================================
        2. INNER TEXT TARGETING (Fixes font sizing and wrapping colors)
        ======================================================== */
        div.stButton > button p {
            color: #94A3B8 !important; /* Default soft gray-blue text */
            font-size: 14px !important;
            font-weight: 500 !important;
            line-height: 1.3 !important;
            margin: 1px !important;
        }

        /* ========================================================
        3. LEFT EDGE ACCENT STRIPS (Mirrors curriculum layout)
        ======================================================== */
        div.stButton:nth-of-type(1) > button {
            border-left: 4px solid #2473F2 !important; /* Main active vibrant blue */
        }

        div.stButton:nth-of-type(2) > button {
            border-left: 4px solid #3B82F6 !important; /* Lighter sky blue */
        }

        div.stButton:nth-of-type(3) > button {
            border-left: 4px solid #60A5FA !important; /* Soft icy blue */
        }

        /* ========================================================
        4. HOVER & FOCUS INTERACTION STATES
        ======================================================== */
        div.stButton > button:hover {
            background-color: #1E293B !important; /* Slightly lighter tone on hover */
            border-color: #2473F2 !important; /* Outer glow matches banner blue */
            transform: translateX(2px) !important; /* Subtle shift forward */
            box-shadow: 0 4px 12px rgba(36, 115, 242, 0.15) !important;
        }

        /* Lights up inner text to pure white when hovered */
        div.stButton > button:hover p {
            color: #FFFFFF !important; 
        }

        /* Click feedback compression */
        div.stButton > button:active {
            transform: scale(0.98) !important;
        }

        /* Remove default focus bounding lines */
        div.stButton > button:focus {
            outline: none !important;
            box-shadow: 0 0 0 2px #101726, 0 0 0 4px #2473F2 !important;
        }
        /* ========================================================
        🎨 PREMIUM SIDEBAR NAVIGATION HUB DESIGN SYSTEM
        ======================================================== */

        /* ========================================================
        🎨 ULTIMATE NAVIGATION HUB ENFORCEMENT STYLE
        ======================================================== */

        /* 1. Target the links directly using the data-testid wrapper */
        [data-testid="stSidebar"] [data-testid="stPageLink"] a,
        [data-testid="stSidebarNav"] .stPageLink a,
        div.stPageLink > a {
            width: 100% !important;
            min-height: 54px !important; /* Taller, premium buttons */
            background-color: #101726 !important; /* Perfect match with curriculum box */
            border: 1px solid rgba(36, 115, 242, 0.18) !important; /* Subtle blue outline */
            border-radius: 12px !important;
            padding: 14px 18px !important; /* Spacious inner breathing room */
            margin-bottom: 12px !important; /* Generous gap BETWEEN navigation blocks */
            transition: all 0.2s ease-in-out !important;
            text-decoration: none !important;
            
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
        }

        /* 2. Target the inner text block elements directly */
        [data-testid="stSidebar"] [data-testid="stPageLink"] p,
        [data-testid="stSidebar"] [data-testid="stPageLink"] span,
        div.stPageLink p {
            color: #94A3B8 !important; /* Matching soft gray-blue text */
            font-size: 15px !important; /* Makes the font size noticeably bigger */
            font-weight: 600 !important; /* Strong semi-bold weight */
            line-height: 1.4 !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 3. Hover state animations */
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover,
        div.stPageLink > a:hover {
            background-color: #1E293B !important;
            border-color: #2473F2 !important;
            transform: translateX(4px) !important; /* Elegant little slide nudge forward */
            box-shadow: 0 4px 14px rgba(36, 115, 242, 0.25) !important;
        }

        /* Force text to turn white on hover */
        [data-testid="stSidebar"] [data-testid="stPageLink"] a:hover p,
        div.stPageLink > a:hover p {
            color: #FFFFFF !important;
        }

        /* 4. Highlight the CURRENT active page link item with a left border strip */
        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"],
        div.stPageLink > a[aria-current="page"] {
            background-color: #101726 !important;
            border-left: 5px solid #2473F2 !important; /* Left active accent strip */
            border-color: rgba(36, 115, 242, 0.4) !important;
        }

        [data-testid="stSidebar"] [data-testid="stPageLink"] a[aria-current="page"] p,
        div.stPageLink > a[aria-current="page"] p {
            color: #FFFFFF !important; /* Current page text turns white */
            font-weight: 700 !important; /* Bold current page text */
        }

        </style>
        """, unsafe_allow_html=True)
    st.html(f"""
            <style>
            @media (min-width: 768px) {{
            [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
            [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: -2.4rem !important; padding-top: 0rem !important; }}
            [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container {{ padding-top: 1.5rem !important; margin-top: 0rem !important; }}
            }}
            @media (max-width: 1000px) {{
            [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
            [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: 0rem !important; padding-top: 0.5rem !important; }}
            }}
            [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container {{ padding-top: 1rem !important; }}
            [data-testid="stHeader"] button {{ background-color: rgba(255, 255, 255, 0.1) !important; border-radius: 4px !important; z-index: 999999 !important; }}
            [data-testid="stSidebarUserContent"] {{ padding-top: 0rem !important; margin-top: 0rem !important; }}
            
            /* 🎯 THE CRITICAL ARCHITECTURAL FIX: 
                Excludes the voice recording button element key from global style alterations */
            div.stButton > button:not([key*="mwalimu_voice_recorder"]) {{
            transition: all 0.2s ease-in-out !important;
            }}
            div.stButton > button:not([key*="mwalimu_voice_recorder"]):hover {{
            border-color: #1E3A8A !important;
            color: #1E3A8A !important;
            box-shadow: 0 2px 8px rgba(30, 58, 138, 0.1) !important;
            }}
            </style>
            """)

    