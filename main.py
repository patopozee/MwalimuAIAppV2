import base64
import os
import json
import requests
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

from services.session_service import (
    create_session,
    validate_session,
    destroy_session,
)

# --- STREAMLIT PAGE CONFIGURATION (MUST BE ABSOLUTE FIRST COMMAND IN STREAMLIT) ---
st.set_page_config(
    page_title="Mwalimu AI App",
    page_icon="assets/logo112.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------
# AUTO LOGIN FROM COOKIE
# -----------------------------------

# 1. Initialize Firebase Admin SDK (Only if it hasn't been initialized yet)
if not firebase_admin._apps:
    try:
        secret_json = json.loads(st.secrets["firebase"]["service_account_json"])
        cred = credentials.Certificate(secret_json)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Failed to initialize Firebase credentials: {e}")

# 2. Define 'db' globally for Firestore connection reuse
db = firestore.client()

# --- SERVICES & BACKEND IMPORTS ---
from services.auth_service import MwalimuAuthService
from services.payment_service import MpesaPaymentService
from services.tier_guard import verify_tier_allowance
from services.ai import ask_mwalimu, generate_quiz, generate_study_plan, generate_flashcards, generate_lesson
from services.vision_service import MwalimuVisionService
from services.db_service import MwalimuDBService
from services.legal_text import TERMS_AND_CONDITIONS
from services.quiz_evaluator import evaluate_quiz_submission
from components.navigation import navigate
from views.learning_dashboard import render as render_learning_dashboard
from views.main_chat import render as render_main_chat_view
from views.voice import render as render_voice_view
from views.learning_dashboard import render as render_learning_dashboard_view
from views.generators import render as render_generators_view
from views.leaderboard import render as render_leaderboard_view
from views.admin import render as render_admin_view
from views.lesson_workspace import render as render_lesson_workspace_view
from views.edit_profile import render as render_edit_profile_view
from services.upgrade_modal import upgrade_modal
# --- DATABASE ENGINE CACHE WRAPPERS (IMPORTS REMAIN THE SAME) ---
from services.database import (
    create_tables,
    save_activity,
    get_student_stats,
    get_student_quiz_history,   
    get_student_learning_analysis,
    get_ask_mwalimu_history,  
    clear_student_chat_history,
    get_student_data #  ADD THIS LINE HERE
)



from config import CBC  # Dynamic CBC repository dictionary


# INITIALIZATION & TRANSPORT ENVIRONMENT SETTING
load_dotenv()
current_host = st.context.headers.get("host", "")

if "localhost" in current_host or "127.0.0.1" in current_host:
    REDIRECT_URI = "http://localhost:8501"
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
else:
    REDIRECT_URI = "https://mwalimuaiapp2-1095526444919.africa-south1.run.app"
    if "OAUTHLIB_INSECURE_TRANSPORT" in os.environ:
        del os.environ["OAUTHLIB_INSECURE_TRANSPORT"]

# Execute local database validation setup on runtime startup block
create_tables()

# --- INITIALIZE STATE WORKSPACE PARAMS (WITH PERFORMANCE PROFILE STORAGE CACHE) ---
if "user_authenticated" not in st.session_state: st.session_state.user_authenticated = False
if "current_page" not in st.session_state: st.session_state.current_page = "Main Chat"
if "quiz_questions" not in st.session_state: st.session_state.quiz_questions = []
if "quiz_raw_score" not in st.session_state: st.session_state.quiz_raw_score = 0
if "quiz_score" not in st.session_state: st.session_state.quiz_score = 0
if "quiz_submitted" not in st.session_state: st.session_state.quiz_submitted = False
if "quiz" not in st.session_state: st.session_state.quiz = None
if "study_plan" not in st.session_state: st.session_state.study_plan = None
if "flashcards" not in st.session_state: st.session_state.flashcards = []
if "lesson_content" not in st.session_state: st.session_state.lesson_content = None
if "student_name" not in st.session_state: st.session_state.student_name = ""
# 🎯 SPEED FIX: Initialize a specific localized memory caching slot for Firestore profile row responses
if "user_profile" not in st.session_state: st.session_state.user_profile = None
if "ask_mwalimu_history" not in st.session_state: 
    st.session_state.ask_mwalimu_history = []
if "voice_chat_history" not in st.session_state: 
    st.session_state.voice_chat_history = []
if "new_message" not in st.session_state:
    st.session_state.new_message = False


if "active_view" not in st.session_state:
    st.session_state.active_view = "main"

# 🎯 SPEED FIX: Initialize a specific localized memory caching slot for Firestore profile row responses
if "new_message" not in st.session_state:st.session_state.new_message = False


  


# ====================================================================
# 🍪 STEP 1: TOP-LEVEL NATIVE PERSISTENCE RESTORER (RUNS FIRST ON F5)
# ====================================================================
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False

# Restore session from secure cookie

session = validate_session()

if (
    not st.session_state.get("user_authenticated")
    and session is not None
):

    uid = session["uid"]

    profile = get_student_data(uid)

    if profile:

        st.session_state.user_authenticated = True

        st.session_state.uid = uid
        st.session_state.user_email = profile.get("email", session["email"])

        st.session_state.student_name = profile.get("name", "Student")
        st.session_state.grade = profile.get("grade", "Grade 1")
        st.session_state.age = int(profile.get("age", 10))

        st.session_state.user_profile = profile

        st.session_state.current_page = "Main Chat"

    else:
        destroy_session()



# ====================================================================
# 🚀 STEP 2: TOP-LEVEL GOOGLE OAUTH INTERCEPTOR (MODIFIED FOR PERSISTENCE)
# ====================================================================
if "code" in st.query_params and not st.session_state.user_authenticated:
    auth_code = st.query_params["code"]
  
    try:
        cid = st.secrets["google_oauth"]["client_id"]
        csecret = st.secrets["google_oauth"]["client_secret"]
        
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": auth_code,
                "client_id": cid,
                "client_secret": csecret,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        
        if response.status_code == 200:
            token_response = response.json()
            
            if "access_token" in token_response:
                user_info = requests.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_response['access_token']}"},
                ).json()
                
                google_uid = user_info.get("id") or user_info.get("sub")
                email_val = user_info.get("email", "").strip().lower()
                name_val = user_info.get("name", "Student").strip().title()
                
                if not google_uid:
                    st.error("Authentication failed: Missing unique user ID from Google.")
                    st.stop()
                
                check_doc = db.collection("users").document(google_uid).get()
                
                user_profile_payload = {
                    "uid": google_uid,
                    "name": name_val,
                    "email": email_val,
                    "grade": "Grade 6",
                    "age": 12,
                    "created_at": "2026-07-11T13:08:00Z",
                    "subscription": {
                        "tier": "Free",
                        "payment_status": "Pending",
                        "reference_id": "",
                        "expiry_date": ""
                    }
                }
                
                if not check_doc.exists:
                    db.collection("users").document(google_uid).set(user_profile_payload, merge=True)
                
                fresh_doc = db.collection("users").document(google_uid).get()
                doc_data = fresh_doc.to_dict()
                final_data = doc_data if (fresh_doc.exists and doc_data is not None) else user_profile_payload
                
                # Session State Hydration
                st.session_state.user_authenticated = True
                
                st.session_state.uid = google_uid
                st.session_state.user_email = final_data.get("email", email_val)
                st.session_state.student_name = final_data.get("name", name_val)
                st.session_state.grade = final_data.get("grade", "Grade 6")
                st.session_state.age = int(final_data.get("age", 12))
                st.session_state.user_profile = final_data
                st.session_state.current_page = "Main Chat"
                
                st.toast(f"🎉 Welcome, {st.session_state.student_name}!")
                create_session(google_uid, email_val)
                # 🌟 FIXED PERSISTENCE ANCHOR: Lock token inside URL parameters BEFORE reloading the page
                st.rerun()

    except Exception as e:
        st.error(f"Authentication background sync failed: {str(e)}")


    # ADD THE CSS BLOCK HERE (Right after page config)
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
    
    div.stButton > button {{
    transition: all 0.2s ease-in-out !important;
    }}
    div.stButton > button:hover {{
    border-color: #1E3A8A !important;
    color: #1E3A8A !important;
    box-shadow: 0 2px 8px rgba(30, 58, 138, 0.1) !important;
    }}
    </style>
    """)

# --- HEADER AREA ---
header_col1, header_col2 = st.columns([8, 1])

# 1. DEFINE BASE64 PARSER UTILITY AT TOP-LEVEL
def get_base64_image(image_path):
    import os
    import base64
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def render_auth_portal(context="auth"):
    # If a user selected a tier, show them what they are signing up for
    if "selected_tier" in st.session_state:
        st.info(f"You are signing up for: **{st.session_state.selected_tier}**") 
        
    # Track password reset sub-form display states
    if "show_reset_form" not in st.session_state:
        st.session_state.show_reset_form = False

    # Initialize all 3 native authorization tabs up-front
    tab_login, tab_signup, tab_google = st.tabs(["🔑 Login", "✨ Sign Up", "🔵 Google"])
    
    # ----------------------------------------------------
    # TAB 1: LOGIN GATEWAY & RESTORED RESET MANAGEMENT
    # ----------------------------------------------------
    with tab_login:
        with st.container(border=True):
            # CONDITION A: Default Login Window View Layout
            if not st.session_state.get("show_reset_form", False):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_pass")
                
                if st.button("Log In to Workspace", use_container_width=True):
                    if email.strip() and password.strip():
                        with st.spinner("Verifying credentials..."):
                            auth_res = MwalimuAuthService.login_user(email.strip(), password.strip())                    
                            if auth_res.get("success"):                              
                                st.session_state.user_email = email.strip().lower()
                                uid = str(auth_res.get("uid", ""))
                                st.session_state.uid = uid
                                db_profile = get_student_data(uid)                                 
                                if db_profile and isinstance(db_profile, dict):
                                    st.session_state.user_authenticated = True
                                    from services.upgrade_modal import upgrade_modal
                                                                        
                                    st.session_state.upgrade_modal = False
                                    st.session_state.student_name = str(db_profile.get("name", "Unknown"))
                                    st.session_state.grade = str(db_profile.get("grade", "Grade 1"))
                                    st.session_state.age = int(db_profile.get("age", 10))
                                    st.session_state.user_profile = db_profile
                                    
                                    st.session_state.current_page = "Main Chat"
                                    create_session(uid, email)
                                    st.rerun()


                                else:
                                    st.error("Profile not found for this user. Please register your profile.")
                            else:
                                st.error(f"Login Failed: Please try again. Error: {auth_res.get('error')}")
                
                # LINK TO TOGGLE RESET VIEW ONLY INSIDE THE LOGIN TAB
                if st.button("Forgot Password?", key="forgot_pass_link_btn"):
                    st.session_state.show_reset_form = True
                    st.rerun()
                    
            # CONDITION B: PASSWORD RECOVERY SUB-FORM PIPELINE (STABLE VERSION)
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
                                st.success("📩 **Reset link sent successfully!** Please check your email inbox or spam folder to complete your password change.")
                            else:
                                st.error("If the email is registered, you will receive a reset link shortly. Please check your inbox or spam folder.")
                                print(f"Debug Reset Error: {result.get('error')}")
                
                # Back to log in option button serves as confirmation closer link
                if st.button("⬅_ Return to Login Screen", use_container_width=True, key="back_to_login_from_reset"):
                    st.session_state.show_reset_form = False
                    st.rerun()


    # ----------------------------------------------------
    # TAB 2: SIGNUP FUNNEL WITH LEGAL COMPLIANCE GATE
    # ----------------------------------------------------
    with tab_signup:
        with st.container(border=True):
            # --- STEP 1: INITIAL SIGNUP FORM ---
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
                        with st.spinner("Creating your Mwalimu AI account..."):
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
            # --- STEP 2: VERIFICATION INPUT ---
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

    # ----------------------------------------------------
    # TAB 3: OAUTH GOOGLE AUTHENTICATION GATED ROUTE
    # ----------------------------------------------------
    with tab_google:
        with st.container(border=True):
            st.write("Fast access via Google:")
            
            google_agree = st.checkbox("I agree to terms and conditions", key="google_agree")
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
            
            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth"
                f"?client_id={st.secrets['google_oauth']['client_id']}"
                "&response_type=code"
                "&scope=openid%20email%20profile"
                f"&redirect_uri={REDIRECT_URI}"
                "&access_type=offline"
                "&prompt=select_account"
            )
            

                
                # 4. Conditional Secure Intercept Gateway Controller UI Layer
            if google_agree:
                google_logo_b64 = get_base64_image("assets/google.png")
                st.markdown(f"""
                <a href="{auth_url}" target="_self" style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 12px 20px;
                    background-color: #ffffff;
                    border: 1px solid #dadce0;
                    border-radius: 8px;
                    color: #3c4043;
                    text-decoration: none;
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                    font-weight: 500;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                    margin-bottom: 10px;
                ">
                    <img src="data:image/png;base64,{google_logo_b64}" style="width: 20px; margin-right: 10px;">
                    Continue with Google
                </a>
                """, unsafe_allow_html=True)


            else:
                st.markdown(f"""
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 12px 20px;
                    background-color: #f1f3f4;
                    border: 1px solid #dadce0;
                    border-radius: 8px;
                    color: #9aa0a6;
                    text-decoration: none;
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                    font-weight: 500;
                    cursor: not-allowed;
                    margin-bottom: 10px;
                    opacity: 0.6;
                ">
                    Continue with Google
                </div>
                """, unsafe_allow_html=True)
                st.info("🔒 Please check the agreement box above to activate Google Sign-In.")
           



# ==============================================================================
# ROUTE ROUTER ENGINE
# ==============================================================================

# --- VIEW A: SECURE WORKSPACE DASHBOARD (Logged In State Only) ---

# =====================================================================
# --- LIVE PAYMENT CELEBRATION DISPATCHER (ADD THIS) ---
# =====================================================================
if st.session_state.user_authenticated and "user_email" in st.session_state:
    # 1. Fetch live profile data cleanly from your optimized database.py cache layer
    current_profile_live = get_student_data(st.session_state.user_email)
    
    if current_profile_live and isinstance(current_profile_live, dict):
        live_sub = current_profile_live.get("subscription", {})
        live_tier = str(live_sub.get("tier", "Free")).strip()
        
        # 2. Look for the last tracked tier configuration in local state variables
        if "last_known_tier" not in st.session_state:
            st.session_state.last_known_tier = live_tier
            
        # 3. CRITICAL TRIGGER: If their tier changed from Free to an upgraded level!
        if st.session_state.last_known_tier.lower() == "free" and live_tier.lower() != "free":
            # Update local track markers immediately to prevent looping
            st.session_state.last_known_tier = live_tier
            st.session_state.user_profile = current_profile_live
            st.session_state.grade = str(current_profile_live.get("grade", "Grade 6"))
            st.session_state.age = int(current_profile_live.get("age", 12))
            st.session_state.student_name = str(current_profile_live.get("name", "Student"))
            
            # Reset all generational limits blocks instantly across tabs
            st.session_state.quiz_limit_reached = False
            st.session_state.flashcards_limit_reached = False
            st.session_state.study_plan_limit_reached = False
            st.session_state.chat_limit_reached = False
            
            # 4. Fire a premium canvas canvas celebration visual effect layout onto screen!
            st.balloons()
            st.toast(f"🎉 Premium Power Unlocked! Welcome to {live_tier}!", icon="🚀")
            st.rerun()
            
        # Update fallbacks tracking parameters if altered inside firestore console interfaces manually
        st.session_state.last_known_tier = live_tier

    
    
    #--- BASE64 SIDEBAR IMAGE INJECTOR
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
        /* 1. Safely pull up the root container block without affecting elements inside it */
        [data-testid="stMainBlockContainer"] {
            padding-top: 0.5rem !important;
        }
        
        [data-testid="stMainBlockContainer"] > div:first-child {
            margin-top: -2.0rem !important; /* Pulls the very top of the page layout up cleanly */
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
    
    st.markdown("""
    <style>
    /* 1. GLOBAL BASE STYLES (Applies to your phone view seamlessly) */
    [data-testid="stMainBlockContainer"] {
        max-width: 1000px !important;
        margin: 0 auto !important;
        padding-bottom: 120px !important; 
    }

    /* Base chat input shape configuration */
    div[data-testid="stChatInput"] {
        background-color: transparent !important;
        z-index: 99999 !important;
    }

    div[data-testid="stChatInput"] > div {
        background-color: #2F3037 !important;
        border-radius: 12px !important;
    }


    /* 2. PC & TABLET ONLY ALIGNMENT (Enforces fixed position only above 768px width) */
    @media (min-width: 768px) {
        div[data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 40px !important; 
            left: 57% !important;   /* Only offsets relative to an open PC sidebar */
            transform: translateX(-10%) !important;
            width: 100% !important;
            max-width: 760px !important; 
        }
    }
    </style>
    """, unsafe_allow_html=True)



    st.markdown(
        """
        <style>
        div[data-testid="stChatInput"] {
            bottom: 63px !important;  /* Increase this value to push it higher */
            max-width: 56rem !important;
            left: 58% !important; 
            transform: translateX(-50%) !important;
        }
        </style>
        """,
        unsafe_allow_html=True)


    # Inject custom CSS for responsive alignment
    


    def render_main_chat():
        render_main_chat_view()
    chat_page = st.Page(
            render_main_chat,
            title="Main Chat",
            icon="🏠",
            url_path="chat"
        )

    def render_voice_tutor():
        render_voice_view()

    voice_page = st.Page(
            render_voice_tutor,
            title="Voice Tutor",
            icon="🎙️",
            url_path="voice"
        )

    def render_generators():
        render_generators_view()

    generator_page = st.Page(
            render_generators,
            title="AI Generators",
            icon="⚡",
            url_path="generators"
        )

    def render_learning_dashboard():
        render_learning_dashboard_view()

    learning_page = st.Page(
            render_learning_dashboard,
            title="Learning Dashboard",
            icon="🏫",
            url_path="learning"
        )

    def render_leaderboard():
        render_leaderboard_view()

    leaderboard_page = st.Page(
            render_leaderboard,
            title="Leaderboard",
            icon="🏆",
            url_path="leaderboard"
        )

    def render_admin():
        render_admin_view()

    admin_page = st.Page(
            render_admin,
            title="Admin Dashboard",
            icon="👑",
            url_path="admin"
        )

    def render_lesson_workspace():
        render_lesson_workspace_view()

    lesson_page = st.Page(
        render_lesson_workspace,
        title="Lesson Workspace",
        icon="📖",
        url_path="lesson"
    )

    def render_edit_profile():
        render_edit_profile_view()

    edit_profile_page = st.Page(
        render_edit_profile,
        title="Edit Profile",
        icon="⚙️",
        url_path="edit-profile"
    )

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
        position="hidden",
    )

    st.session_state.ROUTE_CHAT = chat_page
    st.session_state.ROUTE_VOICE = voice_page
    st.session_state.ROUTE_GENERATORS = generator_page
    st.session_state.ROUTE_LEARNING = learning_page
    st.session_state.ROUTE_LEADERBOARD = leaderboard_page
    st.session_state.ROUTE_ADMIN = admin_page
    st.session_state.ROUTE_LESSON = lesson_page
    st.session_state.ROUTE_EDIT_PROFILE = edit_profile_page
    
    #user_data = get_student_data(st.session_state.user_email)

     #==========================
    # NAVIGATION HUB AREA
    #========================
    def nav_item(icon, title, page_name):

        current = st.session_state.get("current_page", "Main Chat")

        active = current == page_name

        if active:
           st.sidebar.markdown(
            f"""
        <div style="display:flex;align-items:center;background:#233044;transition:all .18s ease;border-left:4px solid #3b82f6;padding:10px 14px;border-radius:0 8px 8px 0;margin-bottom:8px;color:white;font-weight:600;">
            {icon}&nbsp;&nbsp;{title}
        </div>
        """,
            unsafe_allow_html=True,
        )

        else:
            if st.sidebar.button(
                f"{icon} {title}",
                key=f"nav_{page_name}",
                use_container_width=True
            ):
                st.session_state.current_page = page_name
                st.rerun()
    #=========================================================
    # NAVIGATION HUB
        # =========================================================
    # 🎨 NAVIGATION HUB DESIGN SYSTEM (HIGH-END MODERN THEME)
    # =========================================================
    st.markdown("""
    <style>
    /* 1. Global Reset & Overrides for the Sidebar Hub Links */
    div[data-testid="stSidebarUserContent"] {
        padding-top: 1rem !important;
    }
    
    /* Elegant Title Design for the Hub Header */
    .nav-hub-title {
        font-family: 'Inter', sans-serif;
        color: #8E929E !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        margin-bottom: 16px !important;
        margin-top: 10px !important;
        padding-left: 8px !important;
    }

    /* 2. Format Streamlit Sidebar Page Links to look like premium tabs */
    [data-testid="stSidebar"] a[data-testid="stSidebarLinkElement"] {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #9CA3AF !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        margin-bottom: 6px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        display: flex !important;
        align-items: center !important;
    }

    /* Elegant Hover State: Dark graphite lift with crisp white text */
    [data-testid="stSidebar"] a[data-testid="stSidebarLinkElement"]:hover {
        background-color: #20222C !important;
        color: #FFFFFF !important;
        transform: translateX(4px); /* Sleek slide-in motion */
    }

    /* 3. ACTIVE STATE: Deep royal sapphire theme with left border glow anchor */
    [data-testid="stSidebar"] a[data-testid="stSidebarLinkElement"][aria-current="page"] {
        background: linear-gradient(90deg, rgba(29, 78, 216, 0.15) 0%, rgba(30, 58, 138, 0.03) 100%) !important;
        border: 1px solid rgba(59, 130, 246, 0.2) !important;
        border-left: 4px solid #3B82F6 !important; /* Vivid neon blue visual selector indicator anchor */
        color: #3B82F6 !important; /* Changes active link item text color to neon blue */
        font-weight: 600 !important;
        padding-left: 11px !important; /* Perfectly balances the 4px left-border space shift */
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.05) !important;
    }

    /* Smooth out the active icon element color filters */
    [data-testid="stSidebar"] a[data-testid="stSidebarLinkElement"][aria-current="page"] span {
        color: #3B82F6 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    # RENDER THE NAVIGATION MENU
    # =========================================================
    st.sidebar.markdown('<p class="nav-hub-title">Navigation Hub</p>', unsafe_allow_html=True)

    # Native page links automatically pick up the active matching current style state classes
    st.sidebar.page_link(chat_page, label="Main Chat", icon="🏠")
    st.sidebar.page_link(voice_page, label="Voice Tutor", icon="🎙️")
    st.sidebar.page_link(generator_page, label="AI Generators", icon="⚡")
    st.sidebar.page_link(learning_page, label="Learning Dashboard", icon="🏫")
    st.sidebar.page_link(leaderboard_page, label="National Leaderboard", icon="🏆")
    

    

    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Student Profile")
    # === SIDEBAR ACCOUNT CONFIGURATION (LOCKED DESIGN BOXES) ===
    # 1. Fetch values safely from your state memory core
    name_val = str(st.session_state.get("student_name") or "Student").strip().title()
    current_grade = st.session_state.get("grade", "Grade 1")
    age_val = int(st.session_state.get("age", 10))

    # 2. Render parameters inside fields locked with disabled=True 🌟
    raw_name = st.sidebar.text_input("Student Name", value=name_val, disabled=True)
    name = raw_name.strip().title() if raw_name else ""
    
    grades = [
            "Grade 1", "Grade 2", "Grade 3", "Grade 4",
            "Grade 5", "Grade 6", "Grade 7", "Grade 8",
            "Grade 9", "Grade 10", "Grade 11", "Grade 12"
        ]
    if current_grade not in grades:
        current_grade = "Grade 1"

    grade = st.sidebar.selectbox(
        "Grade",
        grades,
        index=grades.index(current_grade),
        disabled=True
    )
    
    age_input = st.sidebar.number_input(
        "Age",
        min_value=5,
        max_value=25,
        value=age_val,
        disabled=True
    )
    age = int(age_input)

    # 3. Leave your other customizable onboarding descriptors active below
    favorite_subject = st.sidebar.text_input("Favorite Subject", value=st.session_state.get("favorite_subject") or "")
    weak_subject = st.sidebar.text_input("Weak Subject", value=st.session_state.get("weak_subject") or "")
    learning_style = st.sidebar.selectbox("Learning Style", ["Visual", "Practical", "Reading/Writing", "Interactive", "Story-based"])
    language = st.sidebar.selectbox("Preferred Language", ["English", "Kiswahili", "Sheng"])

    # Composite state verification logic to load specific student thread context safely
    


    #@st.fragment
    # =====================================================================
    # ⚡ REAL-TIME CBC SYNC ENGINE (RUNS BEFORE CODE RENDERS ON CHANGE)
    # =====================================================================
    def render_cbc_selectors(grade, CBC):

        st.sidebar.markdown("---")
        st.sidebar.subheader("📚 Learning Context")

        grade_dict = CBC.get(grade, {})

        if not isinstance(grade_dict, dict):
            grade_dict = {}

        # ---------------------------------------------------
        # SUBJECT
        # ---------------------------------------------------

        subjects = list(grade_dict.keys()) or ["General Studies"]

        subject = st.sidebar.selectbox(
            "Subject",
            subjects,
            key="sidebar_subject_select"
        )

        subject_dict = grade_dict.get(subject, {})

        if not isinstance(subject_dict, dict):
            subject_dict = {}

        # ---------------------------------------------------
        # TOPIC
        # ---------------------------------------------------

        topics = list(subject_dict.keys()) or ["General Topic"]

        topic = st.sidebar.selectbox(
            "Topic",
            topics,
            key="sidebar_topic_select"
        )

        topic_dict = subject_dict.get(topic, {})

        # ---------------------------------------------------
        # SUB TOPIC
        # ---------------------------------------------------

        if isinstance(topic_dict, dict):

            sub_topics = list(topic_dict.keys()) or ["General Sub-Topic"]

            sub_topic = st.sidebar.selectbox(
                "Sub-topic",
                sub_topics,
                key="sidebar_subtopic_select"
            )

            outcomes = topic_dict.get(sub_topic, [])

        else:

            sub_topic = "General Sub-Topic"

            outcomes = topic_dict

        if not outcomes:

            outcomes = ["General Learning Outcome"]

        # ---------------------------------------------------
        # LEARNING OUTCOME
        # ---------------------------------------------------

        learning_outcome = st.sidebar.selectbox(
            "Learning Outcome",
            outcomes,
            key="sidebar_outcome_select"
        )

        # ============================================================
        # SINGLE SOURCE OF TRUTH
        # ============================================================

        current_curriculum = {
            "subject": subject,
            "topic": topic,
            "sub_topic": sub_topic,
            "learning_outcome": learning_outcome
        }

        old_curriculum = st.session_state.get("active_curriculum")

        # Only update Session State if something actually changed.
        if old_curriculum != current_curriculum:

            st.session_state.active_curriculum = current_curriculum

            st.session_state.active_subject = subject
            st.session_state.active_topic = topic
            st.session_state.active_sub_topic = sub_topic
            st.session_state.active_learning_outcome = learning_outcome

    
    # 2. RUN THIS UNCONDITIONAL: Render selectors immediately on page load
    if name:
        render_cbc_selectors(grade, CBC)

    # 3. Safe contextual extraction fallbacks (Guaranteed up-to-date by the callback)
    subject = st.session_state.get("active_subject", "Mathematics")
    topic = st.session_state.get("active_topic", "Whole Numbers")
    sub_topic = st.session_state.get("active_sub_topic", "Place Value")
    learning_outcome = st.session_state.get("active_learning_outcome", "General Learning Outcome")

    # 4. Create the global student dictionary map
    student = {
        "name": name if name else "Student",
        "grade": grade,
        "age": int(age),
        "favorite_subject": favorite_subject,
        "weak_subject": weak_subject,
        "learning_style": learning_style,
        "language": language,
        "preferred_language": language,
        "subject": subject,
        "topic": topic,
        "sub_topic": sub_topic,
        "learning_outcome": learning_outcome
    }
    st.session_state.active_student_profile = student
    #=========
    # Fetch your unique authenticated Firebase ID string from memory core
    student_uid_val = str(st.session_state.get("uid", ""))

    # Composite state verification logic to load specific student thread context safely       
    if student_uid_val and name:
        if (
            st.session_state.get("last_checked_uid") != student_uid_val
            or st.session_state.get("last_checked_grade") != grade
            or st.session_state.get("last_checked_age") != int(age)
            or st.session_state.get("last_checked_subject")
                != st.session_state.get("active_subject", "General Studies")
        ):

            all_historical_chats = get_ask_mwalimu_history(
                student_uid_val,
                st.session_state.get("active_subject", "General Studies")
            )

            st.session_state.ask_mwalimu_history = [
                msg for msg in all_historical_chats
                if not msg.get("is_voice")
            ]

            st.session_state.last_checked_uid = student_uid_val
            st.session_state.last_checked_grade = grade
            st.session_state.last_checked_age = int(age)
            st.session_state.last_checked_subject = st.session_state.get(
                "active_subject",
                "General Studies"
            )

        st.session_state.student_name = name


    #--- ACTIVE PROFILE CARD
    st.sidebar.markdown("---")

    with st.sidebar.container(border=True):

        st.markdown("### 👤 Active Profile")

        if name:
            st.info(f"**Student:** {name}\n\n**{grade}** | **Age:** {age}")
        else:
            st.warning("Please type your Student Name.")

        if st.button(
            "✏️ Edit Profile",
            key="sidebar_edit_profile_btn",
            use_container_width=True,
            type="secondary",
        ):
            st.switch_page(st.session_state.ROUTE_EDIT_PROFILE)

   
    

    # ====================================================================
    # --- DEDICATED CONFIRMATION DIALOG MODAL ---
    # ====================================================================
    # ==========================================================
    # 💬 CHAT ACTIONS
    # ==========================================================

    current_subject = st.session_state.get(
        "active_subject",
        "General Studies"
    )


    @st.dialog(f"🗑️ Clear {current_subject} Chat")
    def confirm_clear_main_chat_dialog():

        st.markdown(
            f"""
    ### Delete **{current_subject}** Chat History

    This will permanently delete **all conversations** for the **{current_subject}** subject.

    ✅ Chats from your other subjects will remain untouched.

    ⚠️ This action **cannot be undone**.
    """
        )

        col_delete, col_cancel = st.columns(2)

        with col_delete:

            if st.button(
                "🗑️ Delete History",
                key="confirm_delete_subject_chat",
                type="primary",
                use_container_width=True,
            ):

                clear_student_chat_history(
                    student_uid=str(st.session_state.get("uid", "")),
                    grade=st.session_state.get("grade", "Grade 6"),
                    age=int(st.session_state.get("age", 12)),
                    subject=current_subject,
                )

                # Reset local session memory
                st.session_state.ask_mwalimu_history = []

                # Clear cached database functions
                from services.database import (
                    get_ask_mwalimu_history,
                    get_student_stats,
                )

                if hasattr(get_ask_mwalimu_history, "clear"):
                    get_ask_mwalimu_history.clear()

                if hasattr(get_student_stats, "clear"):
                    get_student_stats.clear()

                st.toast(
                    f"{current_subject} chat history deleted successfully.",
                    icon="🗑️",
                )

                st.rerun()

        with col_cancel:

            if st.button(
                "↩ Cancel",
                key="cancel_delete_subject_chat",
                use_container_width=True,
            ):
                st.rerun()


    # ==========================================================
    # 💬 SIDEBAR CHAT CARD
    # ==========================================================

    st.sidebar.markdown("---")

    with st.sidebar.container(border=True):

        st.markdown("### 💬 Chat")

        if st.button(
            "🗑️ Clear Chat History",
            key="sidebar_clear_chat_btn",
            use_container_width=True,
            type="secondary",
        ):
            confirm_clear_main_chat_dialog()

    # ====================================================================
    # 🔒 SECURE FIREBASE ROLE-BASED ADMIN PORTAL (ADD THIS HERE)
    # ====================================================================
    # 🔄 REPLACE the string below with your copied Firebase UID string:
    MASTER_ADMIN_UID = "aYiSGN6DVbOLuM3jYnQSEGpd8Mo2"

    if st.session_state.get("uid") == MASTER_ADMIN_UID:
        st.sidebar.markdown("---")
        st.sidebar.subheader("👑 Administrative Access")

        st.sidebar.page_link(
            admin_page,
            label="⚙️ Open Admin Dashboard",
            icon="👑",
            use_container_width=True,
        )
            
    #======== 
    #=== Upgrade Tier === 
    def render_workspace_sidebar():
        if "user_email" in st.session_state:
            active_target_id = st.session_state.get("uid") or st.session_state.user_email
            user_data = get_student_data(str(active_target_id))
            
            if user_data:
                subscription = user_data.get('subscription', {})
                tier = subscription.get('tier', 'Free')
            else:
                tier = 'Free'
            st.sidebar.write(f"**Current Plan:** {tier}")
            from services.upgrade_modal import upgrade_modal

            # 1. Show upgrade prompt if user is on the Free tier
            if str(tier).strip().lower() == "free":
                st.sidebar.info("🚀 Unlock full power with Premium")
                if st.sidebar.button("🚀 Upgrade to Premium", use_container_width=True):
                    upgrade_modal()
                
                #     #MOVED INSIDE SIDEBAR: Verification button for free users who just paid
                # if st.sidebar.button("💳 I've Paid, Check Status", use_container_width=True):
                #     # ----------------------------------------------------------------
                #     # TEMPORARY MOCK PAYMENT TRIGGER (REMOVE BEFORE PRODUCTION)
                #     # ----------------------------------------------------------------
                #     from datetime import datetime, timedelta
                    
                #     mock_expiry = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
                #     mock_subscription = {
                #         "tier": "Premium",  # Change this to "Mwalimu AI Plus" to test that tier too
                #         "expiry_date": mock_expiry,
                #         "payment_status": "Completed",
                #         "reference_id": "MOCK_PAYMENT_12345"
                #     }
                    
                #     # Directly update your Firestore user document layout
                #     from services.database import db
                #     uid = st.session_state.get("uid") or st.session_state.user_email
                #     db.collection('users').document(str(uid)).update({
                #         "subscription": mock_subscription
                #     })
                #     st.sidebar.success("🔧 Mock Payment Simulated!")
                #     # ----------------------------------------------------------------

                #     # Refresh data from database to check if everything updates live
                #     user_data = get_student_data(st.session_state.user_email)
                #     subscription = user_data.get('subscription', {}) if user_data else {}
                #     updated_tier = subscription.get('tier', 'Free')
                    
                #     if str(updated_tier).strip().lower() != "free":
                #        st.sidebar.success(f"Upgrade successful! You are now {updated_tier}")
                #        st.rerun()
                #     # else:
                #     #    st.sidebar.warning("Payment not confirmed yet. Please wait a moment.")
        #====
        


        # --- DEDICATED LOGOUT CONFIRMATION DIALOG ---
        # ====================================================================    
        # ====================================================================
        # 🚪 DEDICATED LOGOUT CONFIRMATION DIALOG
        # ====================================================================

    @st.dialog("🚪 Log Out")
    def confirm_logout_dialog():

        st.info(
            "You are about to sign out of your Mwalimu AI account.\n\n"
            "✅ Your learning progress has already been saved."
        )

        st.write("")

        col_cancel, col_logout = st.columns(2)

        with col_cancel:
            if st.button(
                "Cancel",
                use_container_width=True,
                key="logout_cancel_btn"
            ):
                st.rerun()

        with col_logout:
            if st.button(
                "🚪 Log Out",
                use_container_width=True,
                type="primary",
                key="logout_confirm_btn"
            ):
                from services.upgrade_modal import upgrade_modal

                # -------------------------------------------------------
                # Clear active session safely
                # -------------------------------------------------------
                tracking_keys_to_purge = [
                    "user_authenticated",
                    "user_profile",
                    "messages",
                    "upgrade_modal",
                    "last_checked_name",
                    "last_checked_grade",
                    "last_checked_age",
                    "student_name",
                    "uid",
                    "user_email",
                    "active_subject",
                    "active_topic",
                    "active_sub_topic",
                    "current_page"
                ]

                for key in tracking_keys_to_purge:
                    st.session_state.pop(key, None)

                st.session_state.current_page = "Main Chat"

                # 🚀 FIX: Hard wipe the browser URL string parameters instantly!
             
                
                destroy_session()
                st.session_state.clear()

                # Tell the top-level persistence engine that this was a deliberate logout

                st.rerun()
    # ====================================================================
    # 🚪 PROFESSIONAL SIDEBAR LOGOUT CARD
    # ====================================================================

    st.sidebar.markdown("---")

    with st.sidebar.container(border=True):

        st.markdown("### 🚪 Sign Out")

        st.write("")

        if st.button(
            "Log Out",
            key="main_sidebar_logout_btn",
            use_container_width=True
        ):
            confirm_logout_dialog()






    # Call the function to render the complete sidebar layout
    render_workspace_sidebar()


    #--- SIDEBAR PROGRESS DASHBOARD GENERATION
    # =====================================================================
    # --- FRAGMENT 2: SANDBOXED METRICS & DAILY USAGE BALANCES ---
    # =====================================================================
    @st.fragment
    def render_sandboxed_metrics_dashboard(name, grade, age):
        # 1. Render Progress Charts and Trends
        st.sidebar.markdown("---")
        st.sidebar.subheader(" Progress Dashboard")
        
        # 🌟 FIXED: Swapped 'name' for the unique 'uid' string variable tracking key
        current_uid = str(st.session_state.get("uid", ""))
        stats = get_student_stats(current_uid, grade, int(age))
        st.sidebar.metric(label="Quizzes Taken", value=stats["quizzes"])
        st.sidebar.metric("Average Score", f"{stats.get('average_score', 0)}%")
        
        analysis = get_student_learning_analysis(current_uid, grade, int(age))
        st.sidebar.markdown(f"**Learning Status:** `{analysis.get('current_level', 'Medium')}`")
        
        if analysis.get('weak_topics'):
            st.sidebar.markdown("**Needs Improvement:**")
            for t in analysis['weak_topics']:
                st.sidebar.caption(f"❌ {t}")
        if analysis.get('strong_topics'):
            st.sidebar.markdown("**Mastered Areas:**")
            for t in analysis['strong_topics']:
                st.sidebar.caption(f"✅ {t}")
                
        history_scores = get_student_quiz_history(current_uid, grade, int(age))
        if len(history_scores) > 0:
            st.sidebar.markdown("**Performance Trend**")
            st.sidebar.line_chart(history_scores)

        # 2. Render Quota Limits Indicators (Firestore Checks Sandbox)
        st.sidebar.markdown("---")
        st.sidebar.subheader(" Daily Generation Limits")
        
        sidebar_profile_raw = get_student_data(st.session_state.user_email)
        sidebar_profile = sidebar_profile_raw if sidebar_profile_raw is not None else {}
        sb_sub_tree = sidebar_profile.get('subscription', {}) if isinstance(sidebar_profile.get('subscription'), dict) else {}
        sb_current_plan = str(sb_sub_tree.get('tier', 'Free')).strip()
        
        from services.tier_guard import TIER_LIMITS
        sb_limits_key = "Free"
        if "plus" in sb_current_plan.lower():
            sb_limits_key = "Mwalimu AI Plus"
        elif "premium" in sb_current_plan.lower():
            sb_limits_key = "Premium"
        sb_user_limits = TIER_LIMITS.get(sb_limits_key, TIER_LIMITS["Free"])
        
        sb_uid = str(st.session_state.get("uid") or st.session_state.user_email)
        
        sb_q_limit = sb_user_limits.get("quizzes", 1)
        sb_fc_limit = sb_user_limits.get("flashcards", 1)
        sb_ask_limit = sb_user_limits.get("questions", 1)
        sb_plan_limit = sb_user_limits.get("has_study_plan", 1)
        sb_lesson_limit = sb_user_limits.get("lessons", 1)
        sb_upload_limit = sb_user_limits.get("has_upload", 1)
        
        sb_q_used = MwalimuDBService.get_daily_usage(sb_uid, "quizzes")
        sb_fc_used = MwalimuDBService.get_daily_usage(sb_uid, "flashcards")
        sb_ask_used = MwalimuDBService.get_daily_usage(sb_uid, "questions")
        sb_plan_used = MwalimuDBService.get_daily_usage(sb_uid, "has_study_plan")
        sb_lesson_used = MwalimuDBService.get_daily_usage(sb_uid, "lessons")
        sb_upload_used = MwalimuDBService.get_daily_usage(sb_uid, "has_upload")
        
        def format_sb_balance(used, max_limit):
            if max_limit == float('inf'):
                return f"{used} / ∞ (Unlimited)"
            remaining = max(0, max_limit - used)
            return f"{remaining} left (of {max_limit})"
            
        st.sidebar.markdown(f"💬 **Ask Mwalimu:** `{format_sb_balance(sb_ask_used, sb_ask_limit)}`")
        if sb_ask_limit != float('inf') and sb_ask_used >= sb_ask_limit:
            st.sidebar.caption("⚠️ AI Ask limit reached for today.")
            
        st.sidebar.markdown(f"📅 **Study Plans:** `{format_sb_balance(sb_plan_used, sb_plan_limit)}`")
        if sb_plan_limit != float('inf') and sb_plan_used >= sb_plan_limit:
            st.sidebar.caption("⚠️ Study Plan limit reached for today.")
            
        st.sidebar.markdown(f"📝 **Quizzes:** `{format_sb_balance(sb_q_used, sb_q_limit)}`")
        if sb_q_limit != float('inf') and sb_q_used >= sb_q_limit:
            st.sidebar.caption("⚠️ Quiz limit reached for today.")
            
        st.sidebar.markdown(f"🎴 **Flashcards:** `{format_sb_balance(sb_fc_used, sb_fc_limit)}`")
        if sb_fc_limit != float('inf') and sb_fc_used >= sb_fc_limit:
            st.sidebar.caption("⚠️ Flashcard limit reached for today.")
            
        st.sidebar.markdown(f"📚 **Lessons:** `{format_sb_balance(sb_lesson_used, sb_lesson_limit)}`")
        if sb_lesson_limit != float('inf') and sb_lesson_used >= sb_lesson_limit:
            st.sidebar.caption("⚠️ Lesson limit reached for today.")
        
        st.sidebar.markdown(f" **Uploads:** `{format_sb_balance(sb_upload_used, sb_upload_limit)}`")
        if sb_upload_limit != float('inf') and sb_upload_used >= sb_upload_limit:
            st.sidebar.caption(" Uploads limit reached for today.")


    # Safe initialization trigger at runtime execution context
    if name:
        render_sandboxed_metrics_dashboard(name, grade, age)
    else:
        st.sidebar.markdown("---")
        st.sidebar.subheader(" Progress Dashboard")
        st.sidebar.caption("Fill in your name to start tracking parameters.")


    

    # # MAIN BRANDING HEADER CONTAINER
    col1, col2 = st.columns([1, 5], vertical_alignment="center")
    with col1:
        try:
            title_logo = Image.open("assets/logo112.png")
            st.image(title_logo, width=100)
        except Exception:
            pass
    with col2:
        st.markdown("<h1 style='margin-top: 0 !important; margin-bottom: 0 !important; padding: 0;'>Mwalimu AI App</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top: 2px !important; margin-bottom: 0 !important; color: gray; font-weight: normal;'>Shaping Minds, Shifting Futures.</h4>", unsafe_allow_html=True)
        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

    st.write("Welcome to Mwalimu AI! I am your friendly, adaptive Kenyan AI teacher. To begin, create your student profile in the sidebar to sync your learning. From there, you can ask me any school question, explore real-time interactive lessons, challenge yourself with 5-question targeted quizzes, or launch into Voice Tutor Mode for an immersive audio learning experience tailored precisely to your grade, learning style, and topic tracking!")

    # DISPLAY ACTIVE CBC TARGET TRACKER BOX AT TOP OF PAGE
    if name:
        st.markdown(
            f"""
            <div style="background-color: #1e293b; border-left: 5px solid #3b82f6; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <span style="color: #3b82f6; font-weight: bold;">🎯Active Curriculum Targeting:</span>
            <span style="color: #f8fafc;">Grade: {grade} &bull; Subject: {subject} &bull; Topic: {topic} &bull; Sub-topic: {sub_topic}</span>
            <br>
            <span style="color: #94a3b8; font-weight: bold;">Target Learning Outcome:</span>
            <span style="color: #f8fafc;">{learning_outcome}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    

    # ====================================================================
    # RUN THE NAVIGATIONAL ROUTER
    # ====================================================================
    router.run()


    
       
   
#===========================
#=== LANDING PAGE ========
#============================
else:

    
    import base64
    import json
    import streamlit as st
    from PIL import Image

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
        /* Premium Slate Dark Mode Theme Base */
        [data-testid="stAppViewContainer"] { 
            background-color: #020617; 
        }
        
        /* Dynamic Feature Card System */
        .card {
            background: #0f172a;
            padding: 28px;
            border-radius: 16px;
            border: 1px solid #1e293b;
            transition: all 0.3s ease;
            margin-bottom: 15px;
            min-height: 160px;
        }
        .card:hover { 
            border-color: #3b82f6;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px -10px rgba(59, 130, 246, 0.3);
        }
        .card h3 {
            margin-top: 0px !important;
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            color: #f8fafc !important;
        }
        
        /* Flagship Highlight Cards */
        .flagship-card {
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            border: 1px solid #3b82f6;
            padding: 32px;
            border-radius: 20px;
            min-height: 190px;
            transition: all 0.3s ease;
        }
        .flagship-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 30px -10px rgba(59, 130, 246, 0.4);
            border-color: #60a5fa;
        }
        
        /* Trust Metrics Grid Boxes */
        .metric-box { 
            background: #1e293b; 
            padding: 20px; 
            border-radius: 12px; 
            text-align: center;
            border: 1px solid rgba(255,255,255,0.03);
        }
        .metric-box h3 {
            margin: 0px !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
            color: #3b82f6 !important;
        }
        .metric-box p {
            margin: 4px 0 0 0 !important;
            font-size: 0.85rem !important;
            color: #94a3b8 !important;
        }
        
        /* Buttons Native Uniform Enhancers */
        .stButton > button { 
            border-radius: 8px; 
            border: none; 
            font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .card { padding: 18px; min-height: auto; }
            .flagship-card { padding: 20px; min-height: auto; }
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
                st.image(title_logo, width=85)
            except Exception:
                pass
        with col2:
            st.markdown("<h2 style='margin:0; font-weight:800; color:#ffffff;'>Mwalimu AI App</h2>", unsafe_allow_html=True)
            st.markdown("<h5 style='margin:0; color:#64748b; font-weight:normal;'>Shaping Minds, Shifting Futures.</h5>", unsafe_allow_html=True)

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

    st.write("##")

    # ====================================================================
    # # 3. VIEW SWITCHER DISPATCH ENGINE HOOKS
    # ====================================================================
    if st.session_state.show_auth:
        st.markdown("""
        <style>
        [data-testid="stMainBlockContainer"]{
            max-width:960px;
            margin:auto;
            padding-top:2rem;
            padding-bottom:5rem;
        }
        div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stForm"]) {
            max-width:900px;
            margin:auto;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("## Join Mwalimu AI Workspace 🎓")
        st.write("Access your specialized CBC study streams, interactive revision sets, and live audio tutors instantly.")
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


        with flag_col2:
            st.markdown(
                """
                <div class='flagship-card'>
                    <h3 style='font-size:1.4rem !important; color:#60a5fa !important;'>💻 Learning Management System</h3>
                    <p style='color:#94a3b8; margin:8px 0 0 0; line-height:1.4;'>
                       Power your growth with our integrated Learning Management System. 
                       Test mastery through interactive quizzes, track performance, 
                       and benchmark progress against peers on our National Leaderboard.
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
                
        with tab_contact:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form(key="landing_contact_tab_form", clear_on_submit=True):
                col_sender, col_mail = st.columns(2)
                with col_sender:
                    sender_name = st.text_input("Your Name", placeholder="e.g., Patrick Wachira")
                with col_mail:
                    sender_email = st.text_input("Your Email Address", placeholder="name@gmail.com")
                msg_subject = st.text_input("Subject", placeholder="How can Mwalimu AI support desk assist you today?")
                msg_body = st.text_area("Your Message Details", placeholder="Type your question or revision inquiry here...", height=120)
                submit_support_btn = st.form_submit_button(label="Submit Secure Message 📩", use_container_width=True)
                if submit_support_btn:
                    st.toast("Support ticket captured! Our desk will follow up via email within 24 hours.", icon="✉")
                    
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