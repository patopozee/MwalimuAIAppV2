import base64
import os
import json
import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime

# Streamlit Page Setup
st.set_page_config(
    page_title="Mwalimu AI App",
    page_icon="assets/favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <head>
        <title>Mwalimu AI App</title>
        <meta name="description" content="Mwalimu AI is your all-in-one intelligent workspace, precision-engineered for Kenya’s CBC curriculum. We combine empathetic, 
        conversational AI tutoring with a robust Learning Management System to help you master complex topics, automate your study planning, 
        and track your academic milestones—all in one seamless hub.">
    </head>
""", unsafe_allow_html=True)

# -----------------------------------
# FIREBASE & DATABASE INITIALIZATION
# -----------------------------------
if not firebase_admin._apps:
    try:
        secret_json = json.loads(st.secrets["Firebase"]["service_account_json"])
        cred = credentials.Certificate(secret_json)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Failed to initialize Firebase credentials: {e}")

db = firestore.client()

# Services & Module Imports
from services.auth_service import MwalimuAuthService
from services.db_service import MwalimuDBService
from services.legal_text import TERMS_AND_CONDITIONS
from views.main_chat import render as render_main_chat_view
from views.voice import render as render_voice_view
from views.learning_dashboard import render as render_learning_dashboard_view
from views.generators import render as render_generators_view
from views.leaderboard import render as render_leaderboard_view
from views.admin import render as render_admin_view
from views.lesson_workspace import render as render_lesson_workspace_view
from views.edit_profile import render as render_edit_profile_view
from styles.mwalimu_theme import load_theme
from services.auth_helpers import get_or_create_user_profile
from services.support import send_support_email
from components.header import render as render_header
from styles.sidebar import load as load_sidebar_style
from components.sidebar import render as render_sidebar
from components.learning_context import render as render_learning_context
from services.database import create_tables, get_student_data
from services.session_service import validate_session, create_session, update_session
from streamlit_cookies_controller import CookieController
from config import CBC

# ONLY initialize and run cookie mechanics if we are NOT in the middle of a Google OAuth callback!
is_oauth_callback = "code" in st.query_params

if not is_oauth_callback:
    cookies_controller = CookieController()
else:
    cookies_controller = None
load_dotenv()

# Dynamic Redirect URI Resolution
def resolve_redirect_uri():
    headers = {}
    if hasattr(st, "context") and hasattr(st.context, "headers"):
        headers = st.context.headers or {}
    
    host = headers.get("x-forwarded-host") or headers.get("host") or ""

    if "localhost" in host or "127.0.0.1" in host:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        return "http://localhost:8501"
    elif "mwalimuaiapp2" in host:
        return "https://mwalimuaiapp2-1095526444919.africa-south1.run.app"
    else:
        return "https://app.mwalimuaiapp.com"

REDIRECT_URI = resolve_redirect_uri()
create_tables()

# ============================================================
# RESTORE USER SESSION + WORKSPACE
# ============================================================
# RESTORE USER SESSION + WORKSPACE
# ============================================================
if "subscription_expiry_checked" not in st.session_state:
    st.session_state.subscription_expiry_checked = False
if "session_checked" not in st.session_state:
    st.session_state.session_checked = False

# ONLY attempt to read session cookies if we aren't handling an incoming Google User
if cookies_controller is not None:
    if not st.session_state.get("user_authenticated", False) and not st.session_state.session_checked:
        session_data = validate_session()
        
        if session_data:
            uid = session_data.get("uid")
            if uid:
                profile = get_student_data(uid)
                if profile:
                    st.session_state.user_authenticated = True
                    st.session_state.uid = uid
                    st.session_state.user_email = profile.get("email", session_data.get("email", ""))
                    st.session_state.student_name = profile.get("name", "Student")
                    st.session_state.grade = profile.get("grade", "Grade 1")
                    st.session_state.age = int(profile.get("age", 10))
                    st.session_state.user_profile = profile
                    workspace = session_data.get("workspace") or {}
                    st.session_state.current_page = workspace.get("current_page", "Main Chat")
                    st.session_state.active_view = workspace.get("active_view", "main")
                    st.session_state.session_checked = True
                else:
                    st.session_state.session_checked = True
            else:
                st.session_state.session_checked = True
        else:
            st.session_state.session_checked = True
else:
    # If it is an OAuth callback, don't let cookie restoration block the execution path
    pass


# ============================================================
# DEFAULT SESSION STATE INITIALIZATIONS
# ============================================================
default_states = {
    "user_authenticated": False,
    "current_page": "Main Chat",
    "active_view": "main",
    "quiz_raw_score": 0,
    "quiz_score": 0,
    "quiz_submitted": False,
    "quiz": None,
    "study_plan": None,
    "flashcards": [],
    "lesson_content": None,
    "student_name": "",
    "user_profile": None,
    "ask_mwalimu_history": [],
    "voice_chat_history": [],
    "new_message": False
}

for key, val in default_states.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ====================================================================
# STEP 2: TOP-LEVEL GOOGLE OAUTH INTERCEPTOR
# ====================================================================

# Add UI Styling
st.html("""
    <style>
    @media (min-width: 768px) {
    [data-testid="stHeader"], header { background-color: transparent !important; height: 3.5rem !important; }
    [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] { margin-top: -4.4rem !important; padding-top: 0rem !important; }
    [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container { padding-top: 1.5rem !important; margin-top: 0rem !important; }
    }
    @media (max-width: 1000px) {
    [data-testid="stHeader"], header { background-color: transparent !important; height: 3.5rem !important; }
    [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] { margin-top: 0rem !important; padding-top: 0.5rem !important; }
    }
    [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container { padding-top: 1rem !important; }
    [data-testid="stHeader"] button { background-color: rgba(255, 255, 255, 0.1) !important; border-radius: 4px !important; z-index: 999999 !important; }
    [data-testid="stSidebarUserContent"] { padding-top: 0rem !important; margin-top: 0rem !important; }
    
    div.stButton > button {
    transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:hover {
    border-color: #1E3A8A !important;
    color: #1E3A8A !important;
    box-shadow: 0 2px 8px rgba(30, 58, 138, 0.1) !important;
    }
    </style>
    """)

# Helper Utilities
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def render_auth_portal(context="auth"):
    if "selected_tier" in st.session_state:
        st.info(f"You are signing up for: **{st.session_state.selected_tier}**") 
        
    if "show_reset_form" not in st.session_state:
        st.session_state.show_reset_form = False

    tab_login, tab_signup, tab_google = st.tabs(["🔑 Login", "✨ Sign Up", "🔵 Google"])
    
    with tab_login:
        with st.container(border=True):
            if not st.session_state.get("show_reset_form", False):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_pass")
                
                if st.button("Log In to Workspace", use_container_width=True):
                    if email.strip() and password.strip():
                        with st.spinner("Verifying credentials..."):
                            auth_res = MwalimuAuthService.login_user(email.strip(), password.strip())                    
                            if auth_res.get("success"):
                                uid = str(auth_res["uid"])
                                db_profile = get_student_data(uid)
                                if db_profile:
                                    create_session(uid, db_profile["email"])
                                    st.session_state.user_authenticated = True
                                    st.session_state.session_checked = True
                                    st.session_state.uid = uid
                                    st.session_state.user_email = db_profile["email"]
                                    st.session_state.student_name = db_profile["name"]
                                    st.session_state.grade = db_profile["grade"]
                                    st.session_state.age = int(db_profile["age"])
                                    st.session_state.user_profile = db_profile
                                    st.session_state.current_page = "Main Chat"
                                    st.session_state.active_view = "main"
                                    update_session()
                                    st.success("Login successful! Redirecting...")
                                    st.rerun()
                                else:
                                    st.error("Profile not found for this user. Please register your profile.")
                            else:
                                st.error(f"Login Failed: {auth_res.get('error')}")

                if st.button("Forgot Password?", key="forgot_pass_link_btn"):
                    st.session_state.show_reset_form = True
                    st.rerun()
            else:
                st.markdown("### 🔄 Reset Password")
                reset_email = st.text_input("Enter your registered email", key="pwd_reset_email_input")
                if st.button("Send Reset Link", use_container_width=True, key="execute_send_reset_link"):
                    if not reset_email.strip():
                        st.warning("Please enter your email.")
                    else:
                        with st.spinner("Sending email..."):
                            result = MwalimuAuthService.send_password_reset_email(reset_email.strip())
                            if result.get("success"):
                                st.success("📩 **Reset link sent successfully!** Please check your email inbox.")
                            else:
                                st.error("If the email is registered, you will receive a reset link shortly.")
                
                if st.button("⬅ Return to Login Screen", use_container_width=True, key="back_to_login_from_reset"):
                    st.session_state.show_reset_form = False
                    st.rerun()

    with tab_signup:
        with st.container(border=True):
            if "pending_verification" not in st.session_state:
                st.write("Register a new student account.")
                reg_name = st.text_input("Student Full Name", key="reg_name")
                reg_email = st.text_input("Email Address", key="reg_email")
                col_g, col_a = st.columns(2)
                with col_g:
                    reg_grade = st.selectbox("Current Grade", [f"Grade {i}" for i in range(1, 13)], index=5, key="reg_grade")
                with col_a:
                    reg_age = st.number_input("Age", min_value=5, max_value=25, value=12, key="reg_age")
                reg_pass = st.text_input("Choose Secure Password", type="password", placeholder="At least 6 characters", key="reg_pass")
                reg_agree = st.checkbox("I agree to terms and conditions", key="reg_agree")
                
                if st.button("Register account", use_container_width=True):
                    if not reg_name.strip():
                        st.warning("Please enter your name.")
                    elif not reg_email.strip():
                        st.warning("Please enter your email address.")
                    elif not reg_pass.strip() or len(reg_pass) < 6:
                        st.warning("Password must be at least 6 characters.")
                    elif not reg_agree:
                        st.error("🔒 You must agree to the terms and conditions before creating an account.")
                    else:
                        with st.spinner("Creating your account..."):
                            reg_res = MwalimuAuthService.register_user(
                                email=reg_email.strip().lower(),
                                password=reg_pass,
                                name=reg_name.strip().title(),
                                grade=reg_grade,
                                age=int(reg_age),
                                tier=st.session_state.get("selected_tier", "Free")
                            )
                            if reg_res.get("success"):
                                st.session_state.pending_verification = reg_email.strip().lower()
                                st.rerun()
                            else:
                                st.error(reg_res.get("error"))
            else:
                st.write(f"Enter the code sent to {st.session_state.pending_verification}")
                entered_code = st.text_input("Verification Code", key="verification_code_entry_input")
                
                if st.button("Complete Registration", use_container_width=True):
                    res = MwalimuAuthService.finalize_registration(
                        st.session_state.pending_verification, 
                        entered_code
                    )
                    if res.get("success"):
                        st.success("Account created! Please sign in via the Login tab.")
                        del st.session_state.pending_verification
                    else:
                        st.error(res.get("error"))

    with tab_google:
        with st.container(border=True):
            st.write("Fast access via Google:")
            google_agree = st.checkbox("I agree to terms and conditions", key="google_agree")
            
            dynamic_redirect = resolve_redirect_uri()
            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth"
                f"?client_id={st.secrets['google_oauth']['client_id']}"
                "&response_type=code"
                "&scope=openid%20email%20profile"
                f"&redirect_uri={dynamic_redirect}"
                "&access_type=offline"
                "&prompt=select_account"
            )
            
            if google_agree:
                google_logo_b64 = get_base64_image("assets/google.png")
                st.markdown(f"""
                <a href="{auth_url}" target="_self" style="
                    display: flex; align-items: center; justify-content: center;
                    padding: 12px 20px; background-color: #ffffff; border: 1px solid #dadce0;
                    border-radius: 8px; color: #3c4043; text-decoration: none;
                    font-family: Arial, sans-serif; font-size: 16px; font-weight: 500;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1); margin-bottom: 10px;
                ">
                    <img src="data:image/png;base64,{google_logo_b64}" style="width: 20px; margin-right: 10px;">
                    Continue with Google
                </a>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="
                    display: flex; align-items: center; justify-content: center;
                    padding: 12px 20px; background-color: #f1f3f4; border: 1px solid #dadce0;
                    border-radius: 8px; color: #9aa0a6; text-decoration: none;
                    font-family: Arial, sans-serif; font-size: 16px; font-weight: 500;
                    cursor: not-allowed; margin-bottom: 10px; opacity: 0.6;
                ">
                    Continue with Google
                </div>
                """, unsafe_allow_html=True)
                st.info("🔒 Please check the agreement box above to activate Google Sign-In.")
                
# ====================================================================
# STEP 2: TOP-LEVEL GOOGLE OAUTH INTERCEPTOR
# ====================================================================
if "code" in st.query_params and not st.session_state.get("user_authenticated", False):
    auth_code = st.query_params["code"]
    current_redirect = resolve_redirect_uri()
    
    try:
        cid = st.secrets["google_oauth"]["client_id"]
        csecret = st.secrets["google_oauth"]["client_secret"]
        
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": auth_code,
                "client_id": cid,
                "client_secret": csecret,
                "redirect_uri": current_redirect,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        
        token_response = response.json()

        if response.status_code == 200 and "access_token" in token_response:
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token_response['access_token']}"},
                timeout=10
            ).json()
            
            email_val = user_info.get("email", "").strip().lower()
            name_val = user_info.get("name", "Student").strip().title()
            
            try:
                firebase_user = auth.get_user_by_email(email_val)
                firebase_uid = firebase_user.uid
            except auth.UserNotFoundError:
                firebase_user = auth.create_user(email=email_val, display_name=name_val)
                firebase_uid = firebase_user.uid
                
            profile = get_or_create_user_profile(firebase_uid, email_val, name_val)
            create_session(profile["uid"], profile["email"])

            st.session_state.user_authenticated = True
            st.session_state.session_checked = True
            st.session_state.uid = profile["uid"]
            st.session_state.user_email = profile["email"]
            st.session_state.student_name = profile["name"]
            st.session_state.grade = profile.get("grade", "Grade 1")
            st.session_state.age = int(profile.get("age", 10))
            st.session_state.user_profile = profile
            st.session_state.current_page = "Main Chat"
            st.session_state.active_view = "main"

            update_session()

            if "code" in st.query_params:
                del st.query_params["code"]

            st.rerun()
        else:
            error_desc = token_response.get("error_description", token_response.get("error", "Unknown Token Error"))
            st.error(f"Google OAuth Token Exchange Failed ({response.status_code}): {error_desc}")

    except Exception as e:
        st.error(f"Authentication background sync failed: {str(e)}")


# ==============================================================================
# ROUTER ENGINE
# ==============================================================================
from components.subscription import enforce_subscription_expiry


def sync_session_profile(profile: dict, tier: str = "Free"):
    """Syncs live Firestore user profile data into Streamlit session state."""
    st.session_state.user_profile = profile
    st.session_state.user_email = profile.get(
        "email", st.session_state.get("user_email", "")
    )
    st.session_state.student_name = str(profile.get("name", "Student"))
    st.session_state.grade = str(profile.get("grade", "Grade 6"))
    st.session_state.age = int(profile.get("age", 12))
    st.session_state.last_known_tier = tier


if st.session_state.get("user_authenticated") and "user_email" in st.session_state:
    # ---------------------------------------------------------
    # 1. SHOW CUSTOM LOADING CARD WHILE INITIALIZING WORKSPACE
    # ---------------------------------------------------------
    st.markdown(
        """
        <style>
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        .loading-card {
            background-color: #101726;
            border: 1px solid rgba(59,130,246,0.2);
            border-radius: 12px;
            padding: 30px;
            margin: 40px auto;
            max-width: 500px;
            color: #94A3B8;
            animation: pulse 1.5s infinite ease-in-out;
            text-align: center;
            font-weight: 600;
            font-size: 18px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    loader = st.empty()
    loader.markdown(
        '<div class="loading-card">🚀 Setting up your Mwalimu AI Workspace...</div>',
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # 2. RUN HEAVY BACKEND OPERATIONS / DATA FETCHING
    # ---------------------------------------------------------
    uid = st.session_state.get("uid")

    # Enforce Expiry & Fetch Profile Once
    if uid and str(enforce_subscription_expiry(uid) or "").lower() == "free":
        current_profile = get_student_data(str(uid))
        if current_profile:
            sync_session_profile(current_profile, tier="Free")
    else:
        current_profile = get_student_data(st.session_state.user_email)

    # ---------------------------------------------------------
    # 3. CLEAR LOADER BEFORE RENDER
    # ---------------------------------------------------------
    loader.empty()

    # Upgrade Detection & Feature Lock Reset
    if isinstance(current_profile, dict):
        live_sub = current_profile.get("subscription") or {}
        live_tier = str(live_sub.get("tier", "Free")).strip()
        last_tier = st.session_state.get("last_known_tier", live_tier)

        if last_tier.lower() == "free" and live_tier.lower() != "free":
            sync_session_profile(current_profile, tier=live_tier)

            # Reset feature limit flags
            for limit_flag in [
                "quiz",
                "flashcards",
                "study_plan",
                "chat",
            ]:
                st.session_state[f"{limit_flag}_limit_reached"] = False

            st.balloons()
            st.toast(
                f"🎉 Premium Power Unlocked! Welcome to {live_tier}!", icon="🚀"
            )
            st.rerun()

        st.session_state.last_known_tier = live_tier
    #===================================================
    #===================================================
    try:
        with open("assets/logo211.png", "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
            sidebar_bg_style = f"background-image: url('data:image/png;base64,{encoded_logo}') !important;"
    except Exception:
        sidebar_bg_style = ""
        # 🚀 ADD THIS SNIPPET HERE TO MAKE THE LOGO APPEAR
        # 🚀 UPDATED: Centered sidebar logo with proper spacing below it
    st.markdown(f"""
        <style>
        [data-testid="stSidebarHeader"] {{
            min-height: 90px !important; /* Increased height to create safe vertical breathing room */
            {sidebar_bg_style}
            background-size: contain !important;
            background-repeat: no-repeat !important;
            background-position: center center !important; /* Centered horizontally and vertically */
            margin-bottom: 1.5rem !important; /* Replaced negative margin with positive padding to push elements down */
            padding-bottom: 10px !important;
        }}
        </style>
        """, unsafe_allow_html=True)
    
        
    # GLOBAL UI & CSS LAYOUT SETTINGS
    st.html("""
        <style>
        html {
            font-size: 14px !important; /* Slightly downsizes default standard text */
        }
        section[data-testid="stSidebar"] {
            width: 320px !important; /* Reduced from 320px to fit scaled screens */
        }
        /* 1. Safely pull up the root container block without affecting elements inside it */
        [data-testid="stMainBlockContainer"] {
        padding-top: 0.5rem !important;
        }
        [data-testid="stMainBlockContainer"] > div:first-child {
        margin-top: -5.0rem !important; /* Pulls the very top of the page layout up cleanly */
        }
        /* 2. REPLACED UNSTABLE H1 SELECTOR: Target only the top title element specifically if needed,
        or let standard elements flow normally to prevent overlaps */
        .element-container:has(h1:first-child) {
        margin-top: 0rem !important; /* Resets sub-page headers back to normal flow spacing */
        }
        /* If you explicitly want to pull up ONLY the main app branding logo container at the top */
        div[data-testid="stElementContainer"]:has(img[alt="Mwalimu AI App"]) {
        margin-top: -2.0rem !important;
        }
        </style>
        """)

    # Look for your existing st.html styles block and add this rule inside it:
    

    import streamlit as st

    st.markdown("""
    <style>

    /* Main content */
    [data-testid="stMainBlockContainer"]{
        max-width:900px;
        margin:auto;
        padding-bottom:120px !important;
    }

    /* Chat input */
    div[data-testid="stChatInput"]{
        position:fixed !important;
        bottom:65px !important;

        z-index:999999;

        transition:
            left .25s ease,
            width .25s ease,
            transform .25s ease;

        padding:0 !important;
        background:transparent !important;
    }

    /* Chat box - Optimized Height Profile */
    div[data-testid="stChatInput"] > div{
        background:#2F3037 !important;
        border-radius:14px !important;
        min-height: 55px !important;
        padding-top: 10px !important;
        padding-bottom: 1px !important;
    }

    
    /* Mobile */
    @media (max-width:768px){

    div[data-testid="stChatInput"]{

        left:12px !important;
        right:12px !important;
        width:auto !important;
        transform:none !important;
        bottom:65px !important;

    }

    }

    </style>
    """, unsafe_allow_html=True)

    #=============================================
    #=============================================

    st.iframe(
    """
    <script>

    function updateChatInput(){

        const sidebar =
            window.parent.document.querySelector('section[data-testid="stSidebar"]');

        const chat =
            window.parent.document.querySelector('div[data-testid="stChatInput"]');

        const main =
            window.parent.document.querySelector('[data-testid="stMainBlockContainer"]');

        if(!sidebar || !chat || !main) return;

        const sidebarWidth = sidebar.getBoundingClientRect().width;

        const mainRect = main.getBoundingClientRect();

        chat.style.left = mainRect.left + "px";

        chat.style.width = mainRect.width + "px";

        chat.style.transform = "none";

    }

    updateChatInput();

    const resizeObserver = new ResizeObserver(updateChatInput);

    resizeObserver.observe(
        window.parent.document.querySelector('section[data-testid="stSidebar"]')
    );

    window.parent.addEventListener("resize", updateChatInput);

    setInterval(updateChatInput,300);

    </script>
    """,
    height=1, # Fixed: set to 1 pixel to satisfy Streamlit's validation while staying invisible
    )

    #========================================================
    # RENDER VIEWS
    #========================================================
    def render_main_chat():
        render_main_chat_view()

    chat_page = st.Page(
        render_main_chat,
        title="Main Chat",
        icon="🏠",
        url_path="chat",
    )

    def render_voice_tutor():
        render_voice_view()

    voice_page = st.Page(
        render_voice_tutor,
        title="Voice Tutor",
        icon="🎙️",
        url_path="voice",
    )

    def render_generators():
        render_generators_view()

    generator_page = st.Page(
        render_generators,
        title="AI Generators",
        icon="⚡",
        url_path="generators",
    )

    def render_learning_dashboard():
        render_learning_dashboard_view()

    learning_page = st.Page(
        render_learning_dashboard,
        title="Learning Dashboard",
        icon="📚",
        url_path="learning",
    )

    def render_leaderboard():
        render_leaderboard_view()

    leaderboard_page = st.Page(
        render_leaderboard,
        title="Leaderboard",
        icon="🏆",
        url_path="leaderboard",
    )

    def render_admin():
        render_admin_view()

    admin_page = st.Page(
        render_admin,
        title="Admin Dashboard",
        icon="👑",
        url_path="admin",
    )

    def render_lesson_workspace():
        render_lesson_workspace_view()

    lesson_page = st.Page(
        render_lesson_workspace,
        title="Lesson Workspace",
        icon="📖",
        url_path="lesson",
    )

    def render_edit_profile():
        render_edit_profile_view()

    edit_profile_page = st.Page(
        render_edit_profile,
        title="Edit Profile",
        icon="⚙️",
        url_path="edit-profile",
    )

    from services.upgrade_modal import upgrade_modal
    # ======================================================
    # SAVE ROUTES (Ensure page object components exist)
    # ======================================================
    # ======================================================
    # SAVE ROUTES (Ensure page object components exist)
    # ======================================================
    st.session_state.ROUTE_CHAT = chat_page
    st.session_state.ROUTE_VOICE = voice_page
    st.session_state.ROUTE_GENERATORS = generator_page
    st.session_state.ROUTE_LEARNING = learning_page
    st.session_state.ROUTE_LEADERBOARD = leaderboard_page
    st.session_state.ROUTE_ADMIN = admin_page
    st.session_state.ROUTE_LESSON = lesson_page
    st.session_state.ROUTE_EDIT_PROFILE = edit_profile_page

    # 🚨 ADD THESE STATE LOGIC INITIALIZATIONS HERE:
    if "show_upgrade_modal" not in st.session_state:
        st.session_state.show_upgrade_modal = False

    # ======================================================
    # STREAMLIT MULTI-PAGE DESERIALIZATION ROUTER (FIXED)
    # ======================================================
    route_mapper = {
        "Main Chat": chat_page,
        "Voice Tutor": voice_page,
        "AI Generators": generator_page,
        "Learning Dashboard": learning_page,
        "Leaderboard": leaderboard_page,
        "Admin Dashboard": admin_page,
        "Lesson Workspace": lesson_page,
        "Edit Profile": edit_profile_page
    }
    router = st.navigation(
        [
            chat_page,
            voice_page,
            generator_page,
            learning_page,
            leaderboard_page,
            admin_page,
            lesson_page,
            edit_profile_page,
        ],
        position="hidden"
    )

    # ======================================================
    # RESTORE SAVED WORKSPACE — ONCE PER SESSION
    # ======================================================
    if st.session_state.user_authenticated:
        if not st.session_state.get("workspace_restored", False):
            saved_page = st.session_state.get("current_page", "Main Chat")
            target_page = route_mapper.get(saved_page, chat_page)
            st.session_state.workspace_restored = True
            if router.url_path != target_page.url_path:
                st.switch_page(target_page)

    if st.session_state.get("user_authenticated", False):
        load_theme()
        from styles.sidebar import load as load_sidebar_style
        load_sidebar_style()
        from styles.sidebar import load_style
        load_style()
        
        import components.sidebar as sidebar
        sidebar.render()
        render_header()
        
        # 🚨 LAUNCH THE DIALOG USING PERSISTENT STATE MANAGEMENT HERE:
        if st.session_state.show_upgrade_modal:
            from services.upgrade_modal import upgrade_modal # Update to match your actual file path
            upgrade_modal()
            
        router.run()



     
   
#===========================
#=== LANDING PAGE ========
#============================
else:

    
    import base64
    import json
    import streamlit as st
    from PIL import Image
    st.markdown(
        """
        <style>
            section[data-testid="stSidebar"] {
                display: none !important;
            }

            [data-testid="stSidebarCollapseButton"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            [data-testid="stAppViewContainer"] {
                margin-left: 0 !important;
            }

            [data-testid="stMain"] {
                margin-left: 0 !important;
            }

            [data-testid="stMainBlockContainer"] {
                max-width: 100% !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Initialize image logo data assets cleanly
    try:
        with open("assets/logo211.png", "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
    except Exception:
        sidebar_bg_style = ""

    # 1. Initialize state variables
    if "show_auth" not in st.session_state:
        st.session_state.show_auth = False
    if "viewing_full_terms" not in st.session_state:
        st.session_state.viewing_full_terms = False
    

    # 2. POLISHED ADVANCED CSS INJECTION
    def inject_polished_css():
        st.markdown("""
        <style>
        /* 1. PREMIUM APPMID GROUND MATCH (Matches the deep workspace base layer background) */
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"] { 
            background-color: #0F1117 !important; 
        }
        
        /* 2. THE COMPACT CARD HOVER BLOCKS (Matches your beautiful inside card metrics) */
        .card {
            background: #101726 !important; /* Unified dark navy container hex */
            padding: 22px 24px !important;
            border-radius: 12px !important; /* Smooth curved card border profiles */
            border: 1px solid rgba(36, 115, 242, 0.12) !important; /* Faint signature blue border line */
            transition: all 0.25s ease-in-out !important;
            margin-bottom: 15px !important;
            min-height: 150px !important;
        }
        
        .card:hover { 
            border-color: #2473F2 !important; /* Glows signature action blue on hover */
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 20px rgba(36, 115, 242, 0.15) !important;
        }
        
        .card h3 {
            margin-top: 0px !important;
            font-size: 1.15rem !important;
            font-weight: 700 !important;
            color: #FFFFFF !important;
        }
        
        /* 3. FLAGSHIP CONTAINER INTERACTIVE LINK SECTIONS */
        .flagship-card {
            background: linear-gradient(135deg, #101726 0%, #1E293B 100%) !important;
            border: 1px solid rgba(36, 115, 242, 0.2) !important;
            border-left: 4px solid #2473F2 !important; /* Pulls your beautiful sidebar indicator strip into the grid! */
            padding: 24px !important;
            border-radius: 12px !important;
            min-height: 240px !important;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            transition: all 0.25s ease-in-out !important;
        }
        
        .flagship-card:hover {
            transform: translateY(-2px) !important;
            border-color: #2473F2 !important;
            box-shadow: 0 10px 22px rgba(36, 115, 242, 0.2) !important;
        }
        
        /* 4. TRUST ACCREDITATION METRIC RIBBONS CONTAINER */
        .metric-box { 
            background: #101726 !important; /* Matches inside workspace background tracking boxes */
            padding: 18px !important; 
            border-radius: 12px !important; 
            text-align: center !important;
            border: 1px solid rgba(36, 115, 242, 0.12) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        }
        
        .metric-box h3 {
            margin: 0px !important;
            font-size: 1.8rem !important;
            font-weight: 800 !important;
            color: #2473F2 !important; /* Bold metrics turn your signature vibrant blue */
        }
        
        .metric-box p {
            margin: 6px 0 0 0 !important;
            font-size: 0.85rem !important;
            color: #94A3B8 !important;
        }
        
        /* 5. NATIVE BUTTON LAYOUT UNIFICATION ACCENTS */
        .stButton > button { 
            border-radius: 10px !important; 
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
        }
        
        .stButton > button[type="primary"] {
            background-color: #2473F2 !important;
            border: none !important;
        }
        
        .stButton > button[type="primary"]:hover {
            background-color: #1D4ED8 !important;
            box-shadow: 0 4px 14px rgba(36, 115, 242, 0.4) !important;
        }

        @media (max-width: 768px) {
            .card { padding: 1px; min-height: auto; }
            .flagship-card { padding: 1px; min-height: auto; }
        }
        </style>
        """, unsafe_allow_html=True)


    # Execute CSS styles injection immediately
    inject_polished_css()

    # ====================================================================
    # # 2. TOP BANNER NAVIGATION & HEADER LAYOUT
    # ====================================================================
    left, middle, right = st.columns([6, 1, 3], vertical_alignment="center")
    with left:
        col1, col2 = st.columns([1, 4], vertical_alignment="center")
        with col1:
            try:
                title_logo = Image.open("assets/logo112.png")
                st.image(title_logo, width=120)
            except Exception:
                pass
        with col2:                    
            st.markdown("<h1 style='margin:0; padding:0; line-height:1; font-weight: 10px;'>Mwalimu AI App</h1>", unsafe_allow_html=True)
            st.markdown("<h4 style='margin:-6px 0 0 0;margin-top: 2px; padding:0; line-height:1; color: gray; font-weight: normal;'>Shaping Minds, Shifting Futures.</h4>", unsafe_allow_html=True)
            st.markdown("<div style='margin-bottom: 3px;'></div>", unsafe_allow_html=True)

    with right:
        # Toggle interface view redirection flags safely
        if st.session_state.show_auth:
            if st.button("⬅ Return to Homepage", use_container_width=True):
                st.session_state.show_auth = False
                st.rerun()
        else:
            if st.button("Sign Up / Access Account 🚀", use_container_width=True, type="primary"):
                st.session_state.show_auth = True
                st.rerun()


    # ====================================================================
    # # 3. VIEW SWITCHER DISPATCH ENGINE HOOKS
    # ====================================================================
    if st.session_state.show_auth:

        # ============================================================
        # AUTH PAGE
        # ============================================================

        st.markdown(
            """
            <style>

            /* Hide authenticated sidebar */
            section[data-testid="stSidebar"] {
                display: none !important;
            }

            [data-testid="stSidebarCollapseButton"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            /* Center authentication content */
            [data-testid="stMainBlockContainer"] {
                max-width: 960px !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 2rem !important;
                padding-bottom: 5rem !important;
            }

            /* Keep the actual login/signup forms narrower */
            div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stForm"]) {
                max-width: 900px !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown("## Join Mwalimu AI Workspace 🎓")

        st.write(
            "Access your specialized CBC study streams, interactive revision sets, "
            "and live audio tutors instantly."
        )

        st.write("---")

        render_auth_portal() # Launches your existing Firebase authentication portal forms cleanly

    else:
        # --- DYNAMIC PREMIUM VISUAL LANDING PAGE VIEW HUB ---
        
        # 🌟 A: SPLIT HERO SECTION WITH LIVE CLASSROOM CONTEXT MOCKUP
        hero_txt, hero_vis = st.columns([1.2, 1], gap="large", vertical_alignment="center")
        with hero_txt:
            st.markdown(
                """
                <h1 style="margin:0; line-height:1.15; font-size:3.2rem; font-weight:800;">
                    Your AI Tutor.<br>Your Academic <span style="color:#3b82f6;">Advantage.</span>
                </h1>
                <p style="color:#94a3b8; font-size:1.1rem; margin-top:16px; margin-bottom:24px; line-height:1.5;">
                    Mwalimu AI is your all-in-one intelligent workspace, precision-engineered for Kenya’s CBC curriculum. We combine empathetic, 
                    conversational AI tutoring with a robust Learning Management System to help you master complex topics, 
                    automate your study planning, and track your academic milestones—all in one seamless hub.
                </p>
                """,
                unsafe_allow_html=True
            )
            if st.button("Get Started For Free ✨", key="hero_center_cta_btn", type="primary"):
                st.session_state.show_auth = True
                st.rerun()
        #====        
        with hero_vis:
            # 📱 UPGRADED: Renders a real production dashboard screenshot mockup
            with st.container(border=True):
                st.markdown(
                    "<p style='margin:0 0 12px 0; font-size:0.8rem; color:#64748b; "
                    "font-weight:600; text-transform:uppercase; letter-spacing:0.05em;'>"
                    "📱 Live Chat Dashboard Preview</p>", 
                    unsafe_allow_html=True
                )
                
                try:
                    # Place your screenshot image inside an assets or images folder
                    # (Ensure you save the screenshot file as 'chat_preview.png' inside your assets directory)
                    preview_screenshot = Image.open("assets/chat_preview.png")
                    
                    st.image(
                        preview_screenshot, 
                        caption="Ask Mwalimu AI Workspace", 
                        width="stretch"
                    )
                except Exception:
                    # 🛡️ Fallback if the image file isn't uploaded to your directory path yet
                    st.info("🗣️ **Mwanafunzi:** How do I find the place value of 5 in 452,100?")
                    st.success("🧙‍♂️ **Mwalimu AI:** Ones, Tens, Hundreds... 5 is in the **Ten Thousands** place! ✨")


        st.markdown("<br><br>", unsafe_allow_html=True)

        # 📊 B: VERIFIED LOCALIZED TRUST METRICS RIBBON BANNER
        st.markdown("<h4 style='text-align:center; color:#64748b; font-weight:700; margin-bottom:16px;'>BUILT TO THE HIGHEST ACCREDITED EDUCATION GUIDELINES</h4>", unsafe_allow_html=True)
        metric_cols = st.columns(4)
        metrics_data = [
            ("4,000+", "CBC Topics Built"), 
            ("20,000+", "Learning Outcomes"), 
            ("100%", "KICD Aligned Standards"), 
            ("4.8/5", "Student Satisfaction Rating")
        ]
        for idx, (value_str, label_str) in enumerate(metrics_data):
            with metric_cols[idx]:
                st.markdown(f"<div class='metric-box'><h3>{value_str}</h3><p>{label_str}</p></div>", unsafe_allow_html=True)

        st.markdown("<br><br><br><br>", unsafe_allow_html=True)

        # 🎯 C: EXPLORE CAPABILITIES FEATURE GRID SYSTEM (WITH VISUAL HIERARCHY)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px;">
                <h2 style="font-size: 2.2rem; font-weight: 800; color: #f8fafc; margin:0;">Everything You Need to Excel 🎯</h2>
                <p style="color: #94a3b8; font-size: 1.05rem; margin: 4px 0 0 0;">Powerful digital features designed to help every learner reach their full potential framework.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        st.markdown("""
        <style>
            /* Ensure all flagship cards have the same height for alignment */
            .flagship-card {
                height: 280px !important; /* Adjust this number to fit your longest card */
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
            }
        </style>
        """, unsafe_allow_html=True)
        # Row 1: Flagship Core Highlights (Split 2-Column Focus Layout)
        flag_col1, flag_col2, flag_col3 = st.columns(3, gap="medium")
        with flag_col1:
            st.markdown(
                """
                <div class='flagship-card'>
                    <h3 style='font-size:1.4rem !important; color:#60a5fa !important;'>🎙️ AI Voice Tutor</h3>
                    <p style='color:#94a3b8; margin:8px 0 0 0; line-height:1.4;'>
                        Transform your fluency with hands-free, interactive voice tutoring. 
                        Engage in natural conversation, practice active listening, and get quick, 
                        verbal concept explanations in both English and Kiswahili—perfect for mastering languages while you are on the move.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )

        #================
        with flag_col2:
            st.markdown(
                """
                <div class='flagship-card'>
                    <h3 style='font-size:1.4rem !important; color:#60a5fa !important;'>💻 Learning Management System</h3>
                    <p style='color:#94a3b8; margin:8px 0 0 0; line-height:1.4;'>
                        Power your growth with our integrated Learning Management System. 
                        Test mastery through interactive quizzes, track your performance, 
                        and benchmark progress against peers on our National Leaderboard—plus, 
                        **earn a printable Certificate of Completion** the moment you master an entire course curriculum.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )

        with flag_col3:
            st.markdown(
                """
                <div class='flagship-card'>
                    <h3 style='font-size:1.4rem !important; color:#60a5fa !important;'>💬 Live Chat With Mwalimu AI</h3>
                    <p style='color:#94a3b8; margin:8px 0 0 0; line-height:1.4;'>
                        Get unstuck in seconds. Ask any academic question and receive clear, snackable, step-by-step breakdowns. 
                        Simply upload screenshots of your homework or
                          textbook pages, and let Mwalimu AI provide verified guidance to help you master every challenge.
                    </p>
                </div>
                """, 
                unsafe_allow_html=True
            )
        

        st.write("##")

        # Row 2 & 3: Standard Sub-utilities (Balanced 3-Column Layout Grid)
            # Row 2 & 3: Standard Sub-utilities (Balanced 3-Column Layout Grid Continues)
        sub_col1, sub_col2, sub_col3 = st.columns(3)
        with sub_col1:
            st.markdown("<div class='card'><h3>📊 Performance Tracking</h3><p style='color:#94a3b8;'>Monitor your weakness trends, review historical quiz scores, and track your curriculum mastery growth timeline.</p></div>", unsafe_allow_html=True)
            st.markdown("<div class='card'><h3>🎴 Flashcards Generator</h3><p style='color:#94a3b8;'>Effective active-recall memory tool cards built to make vocabulary memorization and rapid topic revision fast.</p></div>", unsafe_allow_html=True)
        with sub_col2:
            st.markdown("<div class='card'><h3>📝 AI Quizzes Generator</h3><p style='color:#94a3b8;'>Instant customized evaluation practice tests on any CBC topic to challenge yourself before class assignments.</p></div>", unsafe_allow_html=True)
            st.markdown("<div class='card'><h3>🗓️ Personalized Study Plans</h3><p style='color:#94a3b8;'>Get automated, data-driven daily study schedules mapped out specifically to help balance your learning pace.</p></div>", unsafe_allow_html=True)
        with sub_col3:
            st.markdown("<div class='card'><h3>📑 AI Lessons Generator</h3><p style='color:#94a3b8;'>Receive comprehensive markdown lesson plan study summaries tailored exactly to match your personal learning style.</p></div>", unsafe_allow_html=True)
            st.markdown("<div class='card'><h3>📤 Upload PDFs and Images</h3><p style='color:#94a3b8;'>Let Mwalimu AI read your uploaded notes, reference sheets, or textbooks to answer specialized assignment problems.</p></div>", unsafe_allow_html=True)


        # ====================================================================
        # 💳 D: FLEXIBLE TIERED MEMBERSHIP ACCESS SECTION
        # ====================================================================
        def render_tier_card_html(title, price, period, description, card_features, color_bg, is_premium=False, button_key=""):
            border_accent = "#fbbf24" if is_premium else "#3b82f6"
            badge_html = "<span style='background: #fbbf24; color: #020617; font-size: 0.7rem; font-weight: bold; padding: 3px 8px; border-radius: 20px; float: right; letter-spacing: 0.05em;'>POPULAR</span>" if is_premium else ""
            
            features_html = ""
            for item in card_features:
                features_html += f"""
                <li style="margin-bottom: 10px; display: flex; align-items: flex-start; font-size: 0.88rem; line-height: 1.3;">
                    <span style="color: {border_accent}; font-weight: bold; margin-right: 8px; flex-shrink: 0;">✓</span>
                    <div>{str(item)}</div>
                </li>
                """
                
            card_html = f"""
            <div style="background-color: {color_bg}; padding: 24px 20px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.05);
            border-top: 5px solid {border_accent}; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4); min-height: 440px; box-sizing: border-box;
            display: flex; flex-direction: column; color: #ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
                <div>
                    {badge_html}
                    <h3 style="margin: 0 0 6px 0; font-size: 1.35rem; font-weight: 700;">{title}</h3>
                    <div style="margin: 14px 0; display: flex; align-items: baseline;">
                        <span style="color: #ffffff; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.02em;">{price}</span>
                        <span style="color: #94a3b8; font-size: 0.85rem; margin-left: 6px;">{period}</span>
                    </div>
                    <div style="color: #94a3b8; font-size: 0.88rem; margin: 0 0 14px 0; line-height: 1.4; min-height: 36px;">{description}</div>
                </div>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 0 0 16px 0;">
                <ul style="list-style: none; padding: 0; margin: 0; flex-grow: 1;">
                    {features_html}
                </ul>
            </div>
            """
            st.html(card_html)
            st.markdown("<div style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
            if st.button(f"Choose {title}", key=f"btn_action_{button_key}", width="stretch"):
                st.session_state.show_auth = True
                st.session_state.selected_tier = title
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 30px;">
                <h2 style="font-size: 2.3rem; font-weight: 800; color: #f8fafc; margin: 0 0 8px 0;">Flexible Tiered Membership Access</h2>
                <p style="color: #94a3b8; font-size: 1rem; margin: 0;">Pick the right account pace for your regular revisions and curriculum tracking tools.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        col_free, col_basic, col_prem = st.columns(3, gap="medium")
        with col_free:
            render_tier_card_html(
                title="Mwalimu AI Free", price="KES 0", period="Forever Free", 
                description="Basic daily study toolkit for casual learners.", 
                card_features=["15 AI Questions / day", "5 Assessment Quizzes / day", "5 Flashcards generated / day", "1 Basic CBC Lessons / day", "<span style='color: #ef4444;'> No Custom Study Plans</span>","<span style='color: #ef4444;'> No Learning Management</span>", "<span style='color: #ef4444;'> No Voice Tutor access</span>", "<span style='color: #ef4444;'> No Uploads</span>"], 
                color_bg="#0f172a", is_premium=False, button_key="free_tier"
            )
        with col_basic:
            render_tier_card_html(
                title="Mwalimu AI Plus", price="KES 499", period="/ month", 
                description="Enhanced toolkit built for dedicated study sessions.", 
                card_features=["50 AI Questions / day", "15 Assessment Quizzes / day", "30 Flashcards generated / day", "5 CBC Lessons / day", "5 Personalized daily Study Plans / day", "10 Uploads / day", "Learning Management System", "<span style='color: #ef4444;'> No Voice Tutor access</span>"], 
                color_bg="#111827", is_premium=False, button_key="plus_tier"
            )
        with col_prem:
            render_tier_card_html(
                title="Mwalimu Premium", price="KES 999", period="/ month", 
                description="Complete school execution dashboard with full feature access.", 
                card_features=["Unlimited Interactive Prompts", "Unlimited targeted CBC Quizzes", "Unlimited Flashcard summaries", "Full Voice Tutor Mode Enabled", "Personalized daily Study Plans", "Learning Management System","Advanced Weak-Topic Detection", "Personalized CBC Lessons"], 
                color_bg="#030712", is_premium=True, button_key="premium_tier"
            )


        # ====================================================================
        # 📋 E: INFORMATION & FAQ SUPPORT CENTER RESOURCE SECTIONS
        # ====================================================================
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px;">
                <h2 style="font-size: 2rem; font-weight: 700; color: #f8fafc; margin: 0 0 6px 0;">Information & Support Center</h2>
                <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">Got questions or need to review our platform policies? Explore the tabs below.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        tab_faq, tab_contact, tab_terms = st.tabs([" Frequently Asked Questions", " Contact Support", " Terms & Conditions"])
        
        with tab_faq:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander(" How do I pay for Mwalimu AI Plus or Premium?"):
                st.write("Payments are securely handled via **M-Pesa STK Push** dialog request menus directly onto your registered smartphone.")
            with st.expander(" How long does my upgraded tier access last?"):
                st.write("All upgrade packages provide **30 days of complete access** from the payment date. No automated rolling card renewals.")
            with st.expander(" Can I upgrade from Plus to Premium later?"):
                st.write("Yes! You can choose to upgrade or scale your active tier levels at any time from your account panel.")
            with st.expander(" What equipment do I need for the Voice Tutor mode?"):
                st.write("No extra microphone gear or headsets are required! Standard built-in browser microphone access is perfectly fine.")
        #=============
        #       
        with tab_contact:
            st.markdown("### 📞 Contact Mwalimu AI")

            st.info("""
        📧 **Email:** info@mwalimuaiapp.com

        💬 **WhatsApp:** +254 710 694 297

        📞 **Call:** +254 710 694 297
        """)

            with st.form("contact_form", clear_on_submit=True):

                col1, col2 = st.columns(2)

                with col1:
                    sender_name = st.text_input(
                        "Your Name",
                        placeholder="e.g. Patrick Wachira"
                    )

                with col2:
                    sender_email = st.text_input(
                        "Your Email",
                        placeholder="name@gmail.com"
                    )

                phone = st.text_input(
                    "Phone Number (Optional)",
                    placeholder="+254712345678"
                )

                subject = st.text_input(
                    "Subject",
                    placeholder="How can we help you?"
                )

                message = st.text_area(
                    "Message",
                    height=150,
                    placeholder="Type your message here..."
                )

                submitted = st.form_submit_button(
                    "📩 Send Message",
                    use_container_width=True
                )
                if submitted:

                    success = send_support_email(
                        sender_name,
                        sender_email,
                        phone,
                        subject,
                        message
                    )

                    if success:
                        st.success("✅ Your message has been sent successfully.")
                    else:
                        st.error("❌ Failed to send your message.")
                    
        with tab_terms:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.get("viewing_full_terms", False):
                st.markdown("## Standalone Terms & Conditions Center")
                st.caption(" Last Updated: July 2026 | CBC Curriculum Engine Sync")
                st.markdown("---")
                try:
                    from services.legal_text import TERMS_AND_CONDITIONS
                    st.write(TERMS_AND_CONDITIONS)           
                except Exception:
                    st.write("Terms and Conditions statement content script loading from services layer...")
                st.markdown("---")
                if st.button(" Accept & Close Document (Return Home)", use_container_width=True, key="close_terms_overlay"):
                    st.session_state.viewing_full_terms = False
                    st.rerun()
            else:
                st.markdown("### Platform Terms of Service & End-User License Agreement")
                st.write("To ensure complete transparency regarding your data protection, subscription limits, and M-Pesa non-auto-renewal policies under the Kenyan Data Protection Act, please click the button below to view our comprehensive legal agreement.")
                if st.button(" Read Full Terms of Service", key="trigger_terms_overlay", use_container_width=True):
                    st.session_state.viewing_full_terms = True
                    st.rerun()

        # --- CLEAN LOW-PROFILE FOOTER ARCHITECTURE ---
        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.85rem;'>© 2026 Mwalimu AI App. All Rights Reserved. CBC Curriculum Engine.</p>", unsafe_allow_html=True)








#--- FOOTER LOGO RENDERING WITH PERMANENT CENTERED BOTTOM FIX
logo_html_tag = ""
logo_path = "assets/logo112.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    logo_html_tag = f'<img src="data:image/png;base64,{b64}" width="20" style="vertical-align: middle; margin-right: 8px;">'

st.markdown(
    f"""
    <style>
    .sticky-footer-container {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        z-index: 999;
        padding-bottom: 15px;
        text-align: center;
    }}
    .main .block-container {{
        padding-bottom: 90px !important;
    }}
    </style>

    <div class="sticky-footer-container">
        <hr style='margin: 10px auto 15px auto; width: 80%; border: 0; height: 1px; background-image: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0.1), rgba(255,255,255,0));'>
        <p style='color: gray; font-size: 0.85rem; display: flex; align-items: center; justify-content: center; margin: 0;'>
        {logo_html_tag} Mwalimu AI App Version 2.0 | CBC Curriculum Engine | © 2026 All Rights Reserved
        </p>
    </div>
    """,
    unsafe_allow_html=True
)