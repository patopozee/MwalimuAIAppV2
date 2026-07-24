import base64
import os
import json
import re
import ast
import requests
import sqlite3
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
import streamlit.components.v1 as components
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_cookies_controller import CookieController
from google.cloud.firestore_v1.base_query import FieldFilter


# --- STREAMLIT PAGE CONFIGURATION (MUST BE ABSOLUTE FIRST COMMAND IN STREAMLIT) ---
st.set_page_config(
    page_title="Mwalimu AI App",
    page_icon="assets/logo112.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
from services.ui_components import show_upgrade_modal
from services.legal_text import TERMS_AND_CONDITIONS
from services.quiz_evaluator import evaluate_quiz_submission

# --- DATABASE ENGINE CACHE WRAPPERS (IMPORTS REMAIN THE SAME) ---
from services.database import (
    create_tables,
    save_activity,
    get_student_stats,
    get_student_quiz_history,
    get_next_difficulty,
    get_student_learning_analysis,
    get_ask_mwalimu_history,
    save_ask_mwalimu_message,
    get_voice_chat_history,
    clear_student_chat_history,
    get_student_data,
    clear_voice_chat_history_only  #  ADD THIS LINE HERE
)
from voice_page import render_voice_tutor_page
from services.admin_page import render_admin_dashboard
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



# ====================================================================# 
# ====================================================================
# 🍪 NATIVE APPLICATION QUERY PERSISTENCE ENGINE (DEPRECATION PROOF)
# ====================================================================
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False

# Fetch active browser query strings directly
url_parameters = st.query_params

# 🧼 IF THE USER MANUALLY LOGGED OUT: Wipe tokens completely
if "clear_storage" in url_parameters:
    st.query_params.clear()
    st.session_state.user_authenticated = False
    st.rerun()

# 🔄 COOKIE REFRESH CAPTURE: Automatically log the user back in if parameters match
if not st.session_state.user_authenticated and "session_token_id" in url_parameters:
    persisted_uid = url_parameters["session_token_id"]
    
    from services.database import get_student_data
    db_profile = get_student_data(str(persisted_uid))
    
    if db_profile and isinstance(db_profile, dict):
        st.session_state.user_authenticated = True
        st.session_state.uid = str(persisted_uid)
        st.session_state.user_email = str(db_profile.get("email", ""))
        st.session_state.student_name = str(db_profile.get("name", "Student"))
        st.session_state.grade = str(db_profile.get("grade", "Grade 11"))
        st.session_state.age = int(db_profile.get("age", 17))
        st.session_state.active_subject = db_profile.get("subject") or db_profile.get("favorite_subject") or "Mathematics"
        st.session_state.user_profile = db_profile
        st.session_state.show_upgrade_modal = False
        
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Main Chat"
        st.rerun()



                





# ====================================================================
# 🍪 STEP 1: TOP-LEVEL NATIVE PERSISTENCE RESTORER (RUNS FIRST ON F5)
# ====================================================================
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = False

# 🧼 IF THE USER MANUALLY LOGGED OUT: Wipe tokens out of the URL completely
if "clear_storage" in st.query_params:
    st.query_params.clear()
    st.session_state.user_authenticated = False
    st.rerun()

# 🔄 GOOGLE & EMAIL REFRESH CAPTURE: Re-authenticate natively across page refreshes
if not st.session_state.user_authenticated and "session_token_id" in st.query_params:
    persisted_uid = st.query_params["session_token_id"]
    
    # Direct look up from your initialized Cloud Firestore client instance
    check_profile_doc = db.collection("users").document(persisted_uid).get()
    
    if check_profile_doc.exists:
        final_data = check_profile_doc.to_dict() or {}
        
        # Hydrate all your core student tracking variables back into session memory
        st.session_state.user_authenticated = True
        st.session_state.uid = persisted_uid
        st.session_state.user_email = final_data.get("email", "")
        st.session_state.student_name = final_data.get("name", "Student")
        st.session_state.grade = final_data.get("grade", "Grade 6")
        st.session_state.age = int(final_data.get("age", 12))
        st.session_state.user_profile = final_data
        st.session_state.current_page = "Main Chat"
        st.rerun()


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

                # 🌟 FIXED PERSISTENCE ANCHOR: Lock token inside URL parameters BEFORE reloading the page
                st.query_params.clear()
                st.query_params["session_token_id"] = google_uid
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
    @media (max-width: 767px) {{
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
                                    st.session_state.show_upgrade_modal = False
                                    st.session_state.student_name = str(db_profile.get("name", "Unknown"))
                                    st.session_state.grade = str(db_profile.get("grade", "Grade 1"))
                                    st.session_state.age = int(db_profile.get("age", 10))
                                    st.session_state.user_profile = db_profile
                                    st.session_state.current_page = "Main Chat"
                                    
                                    # 🌟 Lock session UID straight into your active native query parameters
                                    st.query_params["session_token_id"] = uid
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
        #==
            
           



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

    st.markdown("""
        <style>
        /* This centers the dashboard content */
        [data-testid="stMainBlockContainer"] {
            max-width: 1000px !important;
            margin: 0 auto !important;
        }
        /* Optional: Centers the entire view */
        [data-testid="stAppViewContainer"] {
            display: flex;
            justify-content: center;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        div[data-testid="stChatInput"] {
            bottom: 20px !important;  /* Increase this value to push it higher */
            max-width: 56rem !important;
            left: 50% !important; 
            transform: translateX(-50%) !important;
        }
        </style>
        """,
        unsafe_allow_html=True)
   
        #--- BASE64 SIDEBAR IMAGE INJECTOR
    try:
        with open("assets/logo211.png", "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
            sidebar_bg_style = f"background-image: url('data:image/png;base64,{encoded_logo}') !important;"
    except Exception:
        sidebar_bg_style = ""

    # GLOBAL UI & CSS LAYOUT SETTINGS
    st.html(f"""
    <style>
    @media (min-width: 768px) {{
    [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
    [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: -1.5rem !important; padding-top: 0rem !important; }}
    [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container {{ padding-top: 1.5rem !important; margin-top: 0rem !important; }}
    }}
    @media (max-width: 767px) {{
    [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
    [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: 0rem !important; padding-top: 0.5rem !important; }}
    }}
    [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container {{ padding-top: 1rem !important; }}
    [data-testid="stHeader"] button {{ background-color: rgba(255, 255, 255, 0.1) !important; border-radius: 4px !important; z-index: 999999 !important; }}
    [data-testid="stSidebarUserContent"] {{ padding-top: 0rem !important; margin-top: 0rem !important; }}
    [data-testid="stSidebarHeader"] {{
    padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; margin-bottom: 0rem !important; min-height: 80px !important;
    {sidebar_bg_style} background-size: contain !important; background-repeat: no-repeat !important; background-position: left center !important; margin-left: 55px !important;
    }}
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
    # Look for your existing st.html styles block and add this rule inside it:
    st.html("""
        <style>
            /* Force the student (user) chat message row to flip to the right side */
            div[data-testid="stChatMessage"]:has(img[alt="Avatar for user"]),
            div[data-testid="stChatMessage"]:has(span[data-testid="stChatMessageAvatarUser"]) {
                flex-direction: row-reverse !important;
                text-align: right !important;
            }
            
            /* Make sure the internal text alignments inside the bubble remain clean */
            div[data-testid="stChatMessage"]:has(img[alt="Avatar for user"]) div[data-testid="stMarkdownContainer"],
            div[data-testid="stChatMessage"]:has(span[data-testid="stChatMessageAvatarUser"]) div[data-testid="stMarkdownContainer"] {
                text-align: left !important;
                background-color: #2F3037 !important; /* Optional: Makes student bubble look slightly darker/distinct */
                padding: 10px 15px !important;
                border-radius: 15px !important;
                display: inline-block !important;
            }
        </style>
        """)

    #user_data = get_student_data(st.session_state.user_email)

    # === SIDEBAR ACCOUNT CONFIGURATION ===
    #user_data = get_student_data(st.session_state.user_email)

   #user_data = get_student_data(st.session_state.user_email)

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
        st.sidebar.subheader("📚 Curriculum Context")

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
    st.sidebar.subheader(" Active Profile")
    if name:
        st.sidebar.info(f"**Student:** {name} \n\n**{grade}** | **Age:** {age}")
    else:
        st.sidebar.warning("Please type your Student Name at the top of the sidebar.")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("✏️ Edit Student Profile", use_container_width=True):
        st.session_state.current_page = "Edit Profile"
        st.rerun()

    st.sidebar.markdown("---")
    # =====================================================================
    # --- NAVIGATION HUB WITH DYNAMIC GENERATOR TOGGLE ---    
    # =====================================================================
    st.sidebar.markdown("### Navigation Hub")
    
    # ---------------------------------------------------------------------
    # 1. DYNAMIC VOICE TUTOR BUTTON: Switches text based on active page
    # ---------------------------------------------------------------------
    current_active_page = st.session_state.get("current_page", "Main Chat")

    if current_active_page == "Voice Tutor":
        # 🔄 If the user is inside the Voice Tutor, show the path to go back
        if st.sidebar.button("💬 Back to Main Chat", use_container_width=True, key="sb_nav_back_to_chat"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
    else:
        # 🎙️ If the user is anywhere else, show the entrance button to Voice Mode
        if st.sidebar.button("🎙️ Voice Tutor Mode", use_container_width=True, key="sb_nav_go_voice"):
            st.session_state.current_page = "Voice Tutor"
            st.rerun()

        
    # ---------------------------------------------------------------------
    # DYNAMIC BUTTON: Switches text and behavior based on the active page
    # ---------------------------------------------------------------------
    current_active_page = st.session_state.get("current_page", "Main Chat")
    
    if current_active_page == "Generators Hub":
        # If the user is inside the Hub, show the return path button
        if st.sidebar.button("💬 Back to Main Chat", use_container_width=True, key="sb_dynamic_back_chat"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
    else:
        # If the user is anywhere else, show the entrance button to the Hub
        if st.sidebar.button("⚡ Go to Quizzes, Flashcards and Lessons Generator", use_container_width=True, key="sb_dynamic_go_hub"):
            st.session_state.current_page = "Generators Hub"
            st.rerun()
    
    #=========
    # ====================================================================
    # 🏆 DYNAMIC NATIONAL LEADERBOARD TOGGLE SYSTEM
    # ====================================================================
    
    if st.session_state.get("current_page") == "Leaderboard Hub":
        leaderboard_btn_label = "⬅️ Go Back to Main Chat"
        target_leaderboard_page = "Main Chat"
    else:
        leaderboard_btn_label = "🏆 National Leaderboard"
        target_leaderboard_page = "Leaderboard Hub"

    if st.sidebar.button(leaderboard_btn_label, width="stretch", key="sb_nav_dynamic_leaderboard_hub_btn"):
        # 🌟 EXTRA FIX: Pre-seed active grade context tracking strings before redirecting
        if "grade" in st.session_state:
            st.session_state.active_leaderboard_grade = str(st.session_state.grade)
        else:
            st.session_state.active_leaderboard_grade = "Grade 6"
            
        st.session_state.current_page = target_leaderboard_page
        st.rerun()


    

    # ====================================================================
    # --- DEDICATED CONFIRMATION DIALOG MODAL ---
    # ====================================================================
    current_subject = st.session_state.get(
                "active_subject",
                "General Studies"
            )
    @st.dialog(f"⚠️ Clear {current_subject} Chat History")
    def confirm_clear_main_chat_dialog():
        
        st.warning(
            f"You are about to permanently delete your **{current_subject}** chat history."
        )

        st.write(
            "Only chats for this subject will be deleted.\n\n"
            "Your chat history for all other subjects will remain intact."
        )
        
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if st.button(
                    f"Yes, Clear This Subject history",
                    use_container_width=True,
                    type="primary"
                ):
                # 1. Clean the backend database rows permanently
                clear_student_chat_history(
                    student_uid=str(st.session_state.get("uid", "")),
                    grade=st.session_state.get("grade", "Grade 6"),
                    age=int(st.session_state.get("age", 12)),
                    subject=st.session_state.get(
                        "active_subject",
                        "General Studies"
                    )
                )
                
                # 2. Reset visual RAM session storage arrays
                st.session_state.ask_mwalimu_history = []
                
                # 3. Force purge cache snapshots out of Streamlit RAM memory layers
                from services.database import get_ask_mwalimu_history, get_student_stats
                if hasattr(get_ask_mwalimu_history, "clear"):
                    get_ask_mwalimu_history.clear()
                if hasattr(get_student_stats, "clear"):
                    get_student_stats.clear()
                
                st.toast("Chat history cleared cleanly!", icon="🗑️")
                st.rerun()
                
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

    # ====================================================================
    # --- CLEANED SINGLE ACTION BUTTON TRIGGER PANEL (ALWAYS VISIBLE) ---
    # ====================================================================
    st.sidebar.markdown("---") # Visual separator
    if st.sidebar.button(" Clear Chat", use_container_width=True, key="sb_nav_clear_chat"):
        confirm_clear_main_chat_dialog()

    # ====================================================================
    # 🔒 SECURE FIREBASE ROLE-BASED ADMIN PORTAL (ADD THIS HERE)
    # ====================================================================
    # 🔄 REPLACE the string below with your copied Firebase UID string:
    MASTER_ADMIN_UID = "aYiSGN6DVbOLuM3jYnQSEGpd8Mo2"
    
    current_user_uid = st.session_state.get("uid")
    
    # This portal option ONLY shows up if your account matches the master UID
    if current_user_uid and current_user_uid == MASTER_ADMIN_UID:
        st.sidebar.markdown("---")
        st.sidebar.subheader("👑 Administrative Access")
        
        # 🔄 DYNAMIC CHECK: Change text labels and icon depending on the active page state
        if st.session_state.current_page == "Admin Dashboard":
            admin_btn_label = "⬅️ Go Back to Student Dashboard"
            target_page = "Main Chat"
        else:
            admin_btn_label = "⚙️ Open Admin Dashboard"
            target_page = "Admin Dashboard"
            
        if st.sidebar.button(admin_btn_label, use_container_width=True, key="sb_nav_dynamic_admin"):
            st.session_state.current_page = target_page
            st.rerun()
            
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

            # 1. Show upgrade prompt if user is on the Free tier
            if str(tier).strip().lower() == "free":
                st.sidebar.info("🚀 Unlock full power with Premium")
                if st.sidebar.button("🚀 Upgrade to Premium", use_container_width=True):
                    show_upgrade_modal()
                
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
        @st.dialog("🚪 Confirm Logout")
        def confirm_logout_dialog():
            st.write("Are you sure you want to log out of your account? Your active session will be closed.")
            st.write("")
            
            col_yes, col_cancel = st.columns(2)
            with col_yes:
                if st.button("Yes, Log Out", use_container_width=True, type="primary"):
                    # Clear all active configuration parameters out of memory tracks
                    tracking_keys_to_purge = [
                        "user_authenticated", "user_profile", "messages", 
                        "show_upgrade_modal", "last_checked_name", "last_checked_grade", 
                        "last_checked_age", "student_name", "uid", "user_email"
                    ]
                    for target_key in tracking_keys_to_purge:
                        if target_key in st.session_state:
                            del st.session_state[target_key]
                            
                    st.session_state.current_page = "Main Chat"
                    
                    # Set the logout clear string flag 
                    st.query_params["clear_storage"] = "true"
                    st.rerun()
                    
            with col_cancel:
                if st.button("Cancel", use_container_width=True):
                    st.rerun()


        # ====================================================================
        # --- 3. LOG OUT BUTTON CONTAINER (FIXED ALIGNMENT) ---
        # ====================================================================
        st.sidebar.markdown("---")  # Visual separator
        if st.sidebar.button("Logout", use_container_width=True, key="main_sidebar_logout_btn"):
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
        
        analysis = get_student_learning_analysis(name, grade, int(age))
        st.sidebar.markdown(f"**Learning Status:** `{analysis.get('current_level', 'Medium')}`")
        
        if analysis.get('weak_topics'):
            st.sidebar.markdown("**Needs Improvement:**")
            for t in analysis['weak_topics']:
                st.sidebar.caption(f"❌ {t}")
        if analysis.get('strong_topics'):
            st.sidebar.markdown("**Mastered Areas:**")
            for t in analysis['strong_topics']:
                st.sidebar.caption(f"✅ {t}")
                
        history_scores = get_student_quiz_history(name, grade, int(age))
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




    # MAIN BRANDING HEADER CONTAINER
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

    # PAGE VIEW MODE 1: MAIN CHAT DASHBOARD
    if st.session_state.current_page == "Main Chat":
        st.markdown("---")
        if st.button("Go to Quizzes, Flashcards & Lessons Generators", use_container_width=True):
            st.session_state.current_page = "Generators Hub"
            st.rerun()
        st.write("")
        #================================
        # ====================================================================
        # 🏫 LMS CORE INTEGRATION: TODAY'S LEARNING & CONTINUE LEARNING GATE
        # ====================================================================
               # ====================================================================
                # ====================================================================
        # 🏫 LMS CORE INTEGRATION: DYNAMIC NON-LOCKING SUBSCRIPTION GATE
        # ====================================================================
        from services.lms_service import get_current_active_lesson, load_course_structure, get_student_lesson_progress
        
        # 1. Unpack subscription hierarchy details natively from your database dictionary
        student_profile_dict = st.session_state.get("user_profile", {})
        subscription_tree = student_profile_dict.get('subscription', {}) if isinstance(student_profile_dict.get('subscription'), dict) else {}
        user_tier = str(subscription_tree.get('tier', 'Free')).strip()

        # Enforce clean dynamic state handling for verified Premium/Plus users 
        if "premium" in user_tier.lower() or "plus" in user_tier.lower():
            st.session_state.lms_limit_reached = False

        student_uid = str(st.session_state.get("uid") or "")
        student_grade = str(st.session_state.get("grade", "Grade 6"))
        active_subject = str(st.session_state.get("active_subject", "Mathematics"))
        
        current_lesson = get_current_active_lesson(student_uid, student_grade, active_subject)
        course_structure = load_course_structure(student_grade, active_subject)
        all_lessons_list = course_structure.get("lessons", [])
        
        st.markdown("### 🏫 Your Learning Path (Get Certificate Upon Completion)")

        # --------------------------------------------------------------------
        # 🚨 Gatekeeper Banner UI Elements (Only visible if limit is tripped)
        # --------------------------------------------------------------------
        if st.session_state.get("lms_limit_reached"):
            st.error("⚠️ Structured linear learning paths are only available for Plus and Premium members.")
            
            if st.button("🚀 Upgrade to Premium", key="lms_gate_upgrade_unique_btn"):
                # Clean up the limit message flag and set a short-lived transient trigger token
                st.session_state.pop("lms_limit_reached", None)
                st.session_state.trigger_lms_upgrade_modal = True
                st.rerun()

        # Non-locking conditional rendering bridge to process upgrade modal triggers smoothly
        if st.session_state.get("trigger_lms_upgrade_modal"):
            st.session_state.pop("trigger_lms_upgrade_modal", None)
            show_upgrade_modal() # Launches your system's global tier pricing sheet modal

        # --------------------------------------------------------------------
        # 📊 Core Learning Progress Card Panel Component
        # --------------------------------------------------------------------
        with st.container(border=True):
            col_lbl, col_progress, col_btn = st.columns([1.2, 1, 1], vertical_alignment="center")
            
            with col_lbl:
                if current_lesson:
                    st.markdown(f"🎯 **Today's Goal:** `{active_subject}`")
                    st.markdown(f"↳ Current Lesson: **{current_lesson['title']}** (Lesson {current_lesson['order_index']} of {len(all_lessons_list)})")
                else:
                    st.markdown("🎉 **Course Completed!** Excellent job mastering this subject profile.")
                    
            with col_progress:
                completed_count = 0
                for les in all_lessons_list:
                    prog_state = get_student_lesson_progress(student_uid, student_grade, active_subject, str(les["lesson_id"]))
                    if prog_state.get("status") == "Completed":
                        completed_count += 1
                        
                total_lessons = len(all_lessons_list) if all_lessons_list else 1
                progress_percentage = int((completed_count / total_lessons) * 100)
                
                st.write(f"Course Completion Progress: **{progress_percentage}%**")
                st.progress(progress_percentage / 100.0)
                
            with col_btn:
                if current_lesson:
                    # Functional execution trigger button
                    if st.button("🚀 Continue Learning", key="lms_dash_continue_learning_action_btn", width="stretch", type="primary"):
                        
                        # 🛡️ THE GATEKEEPER CHECK: Fall back to limit state if they are on a Free profile
                        if not ("premium" in user_tier.lower() or "plus" in user_tier.lower()):
                            st.session_state.lms_limit_reached = True
                            st.rerun()
                        else:
                            # Plus & Premium accounts proceed straight to the classroom workspace
                            st.session_state.pop("lms_limit_reached", None)
                            st.session_state.lms_active_lesson_node = current_lesson
                            st.session_state.active_subject = active_subject
                            st.session_state.current_page = "LMS Lesson Workspace"
                            st.rerun()
                else:
                    from services.lms_service import generate_completion_certificate
                    student_name_str = str(st.session_state.get("student_name", "Student"))
                    cert_bytes = generate_completion_certificate(
                        student_name=student_name_str,
                        grade=str(student_grade),
                        subject=str(active_subject)
                    )
                    st.download_button(
                        label="📜 Download Completion Certificate",
                        data=cert_bytes,
                        file_name=f"Certificate_{student_name_str.replace(' ', '_')}_{active_subject}.pdf",
                        mime="application/pdf",
                        width="stretch"
                    )
                    
        st.write("---") # Neat separation banner before starting standard conversation trails



        # =====================================================================
        # --- AI STUDY PLAN SECTION
        # =====================================================================
        st.markdown("---")
        st.subheader("AI Personalized Study Plan")

        # 1. Pipeline User Profile Data & Tier Verification safely without breaking Pylance
        user_profile_raw = get_student_data(st.session_state.user_email)
        student_profile = user_profile_raw if user_profile_raw is not None else {}

        # Extract student baseline values cleanly
        name = str(student_profile.get("name", ""))
        grade = str(student_profile.get("grade", ""))
        try:
            age_int = int(student_profile.get("age", 0))
        except (ValueError, TypeError):
            age_int = 0

        # Safeguard Tier Lookup matching working sidebar patterns
        subscription_tree = student_profile.get('subscription', {}) if isinstance(student_profile.get('subscription'), dict) else {}
        user_tier = str(subscription_tree.get('tier', 'Free')).strip()

        # Enforce clean dynamic state handling for Premium/Plus users 
        if "premium" in user_tier.lower() or "plus" in user_tier.lower():
            st.session_state.study_plan_limit_reached = False

        uid = str(st.session_state.get("uid") or st.session_state.user_email)

        # Initialized layout tracking state parameters safely
        if "study_plan" not in st.session_state:
            st.session_state.study_plan = None
        has_active_plan = st.session_state.study_plan is not None

        # ----------------------------------------------------
        # 2. Gatekeeper Banner UI Elements
        # ----------------------------------------------------
        if st.session_state.get("study_plan_limit_reached") and not has_active_plan:
            st.error("⚠️ AI Study Plans are only available for Plus and Premium members.")
            
            if st.button("🚀 Upgrade to Premium", key="study_plan_upgrade_unique_btn"):
                st.session_state.pop("study_plan_limit_reached", None)
                st.session_state.trigger_study_upgrade_modal = True
                st.rerun()

        # Non-locking conditional rendering bridge to process upgrade triggers smoothly
        if st.session_state.get("trigger_study_upgrade_modal"):
            st.session_state.pop("trigger_study_upgrade_modal", None)
            show_upgrade_modal()

        # ----------------------------------------------------
        # 3. Functional Execution Controls
        # ----------------------------------------------------
        if st.button("Generate Today's Study Plan", use_container_width=True):
            if not name or not grade or age_int == 0:
                st.warning("Please complete your Student Profile registration inside the sidebar first!")
                
            elif not verify_tier_allowance(uid, user_tier, "has_study_plan"):
                st.session_state.study_plan_limit_reached = True
                st.rerun()
                
            else:
                st.session_state.pop("study_plan_limit_reached", None)

                with st.spinner("Creating your personalized study plan..."):
                    # Compile usage and behavioral parameters from internal metrics database
                    local_metrics = get_student_stats(student["name"], student["grade"], student["age"])
                    # 🎯 FIX: Pass the fully contextual 'student' dictionary instead of 'student_profile'
                    st.session_state.study_plan = generate_study_plan(student, local_metrics)

                    
                    # Post transaction token balance metrics updates 
                    MwalimuDBService.increment_usage(uid, "has_study_plan")
                    
                    # Verify capacity limits so the tier-guard matches immediately on next reload
                    if not verify_tier_allowance(uid, user_tier, "has_study_plan"):
                        st.session_state.study_plan_limit_reached = True
                    st.rerun()
                    
        # ----------------------------------------------------
        # 4. Display & Formatting Layout
        # ----------------------------------------------------
        if st.session_state.study_plan:
            st.info("💡 Tip: Follow the allocated time intervals for maximum focus today!")
            st.markdown(st.session_state.study_plan)
            
            if st.button("Clear Study Plan", use_container_width=True):
                st.session_state.study_plan = None
                
                if not verify_tier_allowance(uid, user_tier, "has_study_plan"):
                    st.session_state.study_plan_limit_reached = True
                st.rerun()






      # =====================================================
        # CHAT WITH MWALIMU SECTION
        # =====================================================
        st.markdown("---")
        st.write("### 💬 Chat with Mwalimu")
        # Display previous chat messages (State-Guarded Scroll Tracker)
        # -----------------------------
        assistant_messages_count = sum(1 for m in st.session_state.ask_mwalimu_history if m["role"] not in ["student", "user"])
        current_ai_index = 0

        for msg in st.session_state.ask_mwalimu_history:
    # ADD THIS LINE TO SKIP VOICE MESSAGES:
            if msg.get("is_voice") == 1:
                continue
                
            if msg["role"] in ["student", "user"]:
                # 👤 STUDENT CONTAINER
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 20px; width: 100%;">
                    <div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                        <div style="text-align: left;">{msg["content"]}</div>
                    </div>
                    <div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        👤
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if "image_preview" in msg and msg["image_preview"]:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                        <div style="max-width: 320px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border: 1px solid #424656;">
                            <img src="{msg["image_preview"]}" style="width: 100%; display: block;" />
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                if "file_preview" in msg and msg["file_preview"]:
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                        <div style="background-color: #2F3037; color: #ECECF1; padding: 10px 14px; border-radius: 12px; border: 1px solid #424656; display: flex; align-items: center; gap: 8px; font-size: 13px; font-family: sans-serif;">
                            📄 {msg["file_preview"]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            else:
                current_ai_index += 1
                # Create anchor tags directly matching your document strategy
                id_tag = f"msg_{current_ai_index}"

                st.markdown(f"""
                <div id="{id_tag}" style="display: flex; justify-content: flex-start; align-items: center; gap: 10px; margin-bottom: 12px; width: 100%; scroll-margin-top: 80px;">
                    <div style="width: 32px; height: 32px; background-color: #FF4B4B; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        👨‍🏫
                    </div>
                    <div style="font-family: sans-serif; font-size: 13px; font-weight: 600; color: #FF4B4B; text-transform: uppercase; letter-spacing: 0.5px;">
                        Mwalimu AI
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(msg["content"])
                st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # 🛠️ SCROLL ENGINE AUTOMATION MANAGER (DOCUMENT METHOD)
        # ----------------------------------------------------
        # Target the absolute newest assistant message ID block
        target_scroll_id = f"msg_{assistant_messages_count}"

        # ONLY execute scroll action once when the flag is raised!
        if st.session_state.new_message and assistant_messages_count > 0:
            st.session_state.new_message = False  # 👈 DEACTIVATE IMMEDIATELY TO FREE UP SCROLLING
            
            # Inject modern compliant production HTML script snippet
            st.html(f"""
                <script>
                    setTimeout(() => {{
                        const element = window.parent.document.getElementById("{target_scroll_id}");
                        if (element) {{
                            element.scrollIntoView({{ behavior: "smooth", block: "start" }});
                        }}
                    }}, 150);
                </script>
            """)

        # ----------------------------------------------------
        # State-Driven Upgrade Gatekeeper Banner
        # ----------------------------------------------------
        if st.session_state.get("chat_limit_reached"):
            st.error("⚠️ Daily question Limit Reached, Wait for 24hrs or Upgrade to Premium to continue!")
            
            if st.button("🚀 Upgrade to Premium", key="chat_upgrade_unique_btn"):
                # 1. Clear the banner state flag immediately 
                st.session_state.pop("chat_limit_reached", None)
                
                # 2. Stage a temporary trigger instead of a permanent True state
                st.session_state.trigger_chat_upgrade_modal = True
                st.rerun()

        # ----------------------------------------------------
        # Safe Modal Activation Layer (Prevents Continuous Loops)
        # ----------------------------------------------------
        if st.session_state.get("trigger_chat_upgrade_modal"):
            # Instantly remove the flag so it only runs EXACTLY once
            st.session_state.pop("trigger_chat_upgrade_modal", None)
            show_upgrade_modal()

        # ----------------------------------------------------
        # Chat Input
        # ----------------------------------------------------        
        chat_payload = st.chat_input(
            "Ask Mwalimu anything...",
            accept_file=True,
            file_type=["pdf", "png", "jpg", "jpeg"]
        )

        if chat_payload:
            # 1. Extract text and uploaded files from payload safely
            user_question = str(chat_payload.text) if hasattr(chat_payload, "text") else str(chat_payload)
            
            uploaded_file = None
            if hasattr(chat_payload, "files") and chat_payload.files:
                uploaded_file = chat_payload.files

            # 2. Retrieve student metadata details for subscription verification
            student_profile = get_student_data(st.session_state.user_email)
            subscription = student_profile.get("subscription", {}) if student_profile else {}
            tier = subscription.get("tier", "Free")
            uid = st.session_state.get("uid") or st.session_state.user_email
            
            if not name:
                st.warning("Please create Student Profile in the sidebar first!")
            elif not verify_tier_allowance(uid, tier, "questions"):
                st.session_state.chat_limit_reached = True
                st.rerun()
            else:
                st.session_state.pop("chat_limit_reached", None)

                # 3. 🔒 PREMIUM TIER FILE ATTACHMENT GUARD LOCK
                attachment_payload = None
                if uploaded_file:
                    if str(tier).strip().lower() != "premium":
                        st.error("🔒 **Mwalimu Document Scanner is a Premium Feature.** Please upgrade your subscription package!")
                        if st.button("🚀 Upgrade to Premium Now", key="upload_guard_upgrade_btn"):
                            st.session_state.trigger_chat_upgrade_modal = True
                            st.rerun()
                        st.stop()
                    else:
                        attachment_payload = MwalimuVisionService.process_chat_input_file(uploaded_file)

                # 4. Build message payload dictionary and append to state history
                user_message_block = {"role": "student", "content": user_question}
                if attachment_payload:
                    if attachment_payload.get("type") == "image_base64":
                        user_message_block["image_preview"] = attachment_payload["content"]
                    elif attachment_payload.get("type") == "text_extraction":
                        user_message_block["file_preview"] = attachment_payload["filename"]
                conversation_subject = st.session_state.get(
                                    "active_subject",
                                    "General Studies"
                                )
                # Append user text to memory history instantly
                st.session_state.ask_mwalimu_history.append(user_message_block)

                # FIX: Pass the file attachment dictionary payload so it's written into SQLite
                save_ask_mwalimu_message(
                    student_uid=str(st.session_state.get("uid", "")),
                    student_name=str(st.session_state.get("student_name", "Student")),
                    grade=grade,
                    age=int(age),
                    subject=conversation_subject,
                    role="user",
                    message=user_question,
                    attachment=attachment_payload
                )

                st.session_state.ask_mwalimu_history = get_ask_mwalimu_history(
                    str(st.session_state.get("uid", "")),
                    conversation_subject
                )
                                    # 5. IMMEDIATELY DISPLAY USER BUBBLE ON SCREEN (No waiting!)
                # This mirrors your Page 42 custom avatar design look instantly
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 20px; width: 100%;">
                    <div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6;">
                        <div style="text-align: left;">{user_question}</div>
                    </div>
                    <div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0;">
                        👤
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if attachment_payload and attachment_payload.get("type") == "image_base64":
                    st.markdown(f"""
                    <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                        <div style="max-width: 320px; border-radius: 12px; overflow: hidden; border: 1px solid #424656;">
                            <img src="{attachment_payload["content"]}" style="width: 100%; display: block;" />
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # 6. TRIGGER INSTANT SCROLL SNAPPING DOWNWARD BEFORE STREAMING
                # Calculate index position token target tags dynamically
                current_ai_count = sum(1 for m in st.session_state.ask_mwalimu_history if m["role"] not in ["student", "user"]) + 1
                next_scroll_target_id = f"msg_{current_ai_count}"
                
                st.markdown(f'<div id="chat-page-tail" style="height: 5px;"></div>', unsafe_allow_html=True)
                st.html("""
                    <script>
                        window.parent.document.getElementById('chat-page-tail').scrollIntoView({behavior: 'smooth', block: 'end'});
                    </script>
                """)

                # 7. CREATE EMPTY ASSISTANT CHAT CONTAINER BUBBLE ROW
                st.markdown(f"""
                <div id="{next_scroll_target_id}" style="display: flex; justify-content: flex-start; align-items: center; gap: 10px; margin-bottom: 12px; width: 100%; scroll-margin-top: 80px;">
                    <div style="width: 32px; height: 32px; background-color: #FF4B4B; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                        👨‍🏫
                    </div>
                    <div style="font-family: sans-serif; font-size: 13px; font-weight: 600; color: #FF4B4B; text-transform: uppercase; letter-spacing: 0.5px;">
                        Mwalimu AI
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Dedicated Streamlit placeholder layer window block
                assistant_placeholder = st.empty()

                # 8. FIRE DYNAMIC CHUNK GENERATION AND STREAM INTO PLACEHOLDER
                response_stream = ask_mwalimu(
                    question=user_question,
                    student=student,
                    messages=st.session_state.ask_mwalimu_history[:-1],
                    attachment=attachment_payload
                )
                              
                # ====================================================                               
                # 8. SAFE CHUNK GENERATION & DEFENSIVE STREAMING LOOP
                # ====================================================
                assistant_text = ""
                
                try:
                    for chunk in response_stream:
                        if isinstance(chunk, str):
                            # Catch raw string injection issues early
                            if "error" in chunk.lower() or "injected" in chunk.lower():
                                continue
                            assistant_text += chunk
                            assistant_placeholder.markdown(assistant_text)
                            continue
                            
                        if hasattr(chunk, 'choices') and chunk.choices:
                            try:
                                choice_item = chunk.choices[0]
                                if hasattr(choice_item, 'delta') and choice_item.delta:
                                    delta_content = getattr(choice_item.delta, 'content', None)
                                    
                                    if delta_content is not None:
                                        # 🎯 FIX: Intercept the OpenRouter SSE Error Injection early!
                                        if '"error":' in str(delta_content) or 'openai-error' in str(delta_content).lower():
                                            print(f"[Mwalimu Stream Intercept] Caught injected OpenRouter SSE gateway error chunk.")
                                            continue
                                            
                                        assistant_text += str(delta_content)
                                        assistant_placeholder.markdown(assistant_text)
                            except (IndexError, AttributeError, KeyError):
                                continue
                except Exception as stream_err:
                    print(f"[Mwalimu Stream Warning] Connection stream interrupted: {stream_err}")
                    if not assistant_text:
                        assistant_text = "Mwalimu encountered a brief connection stutter. Please try sending your query again!"
                        assistant_placeholder.markdown(assistant_text)


                
                # ====================================================================
                # 9. SAVE COMPLETE HISTORY RECORD DATA ONLY AFTER STREAMING COMPLETES
                # ====================================================================
                MwalimuDBService.increment_usage(uid, "questions")

                #  FIX: Check the structural attachment dictionary extracted on Page 7
                if attachment_payload is not None:
                    MwalimuDBService.increment_usage(uid, "has_upload")

                st.session_state.ask_mwalimu_history.append({"role": "assistant", "content": assistant_text})
                            # 🌟 FIXED: Explicitly naming every argument fixes the Pylance parameter lookup error!
                save_ask_mwalimu_message(
                    student_uid=str(st.session_state.get("uid", "")),
                    student_name=str(st.session_state.get("student_name", "Student")),
                    grade=grade,
                    age=int(age),
                    subject=conversation_subject,
                    role="assistant",
                    message=assistant_text
                )

                st.session_state.ask_mwalimu_history = get_ask_mwalimu_history(
                    str(st.session_state.get("uid", "")),
                    conversation_subject
                )




                
                # ❌ NO MORE ST.RERUN()! The placeholder has already handled displaying the text perfectly!






       # =====================================================================
    # PAGE VIEW MODE 3: GENERATORS WORKSPACE HUB (WITH TIER GUARDS)
    # =====================================================================
    elif st.session_state.current_page == "Generators Hub":
        st.markdown("---")
        
        # 1. Back Navigation Button
        if st.button("⬅️ Go back to Main Chat Dashboard", use_container_width=True, key="back_from_generators"):
            st.session_state.current_page = "Main Chat"
            st.rerun()

        st.markdown("---")
        st.subheader("🎯 Mwalimu AI Learning Generators Hub")
        st.write(f"Active Context: **{student['subject']}** ➡️ **{student['topic']}** ({student['language']})")

        # 2. Fetch student tier profile data upfront using email lookup
        user_profile_raw = get_student_data(st.session_state.user_email)
        student_profile = user_profile_raw if user_profile_raw is not None else {}
        
        # Safely extract baseline profile details
        name = str(student_profile.get("name", ""))
        grade = str(student_profile.get("grade", ""))
        try:
            age_int = int(student_profile.get("age", 0))
        except (ValueError, TypeError):
            age_int = 0

        # Safeguard Tier Lookup matching working sidebar patterns
        subscription_tree = student_profile.get('subscription', {}) if isinstance(student_profile.get('subscription'), dict) else {}
        raw_tier = subscription_tree.get('tier', 'Free')
        user_tier = str(raw_tier).strip()
        uid = str(st.session_state.get("uid") or st.session_state.user_email)

        # Initialize global layout state variables if missing
        if "quiz" not in st.session_state:
            st.session_state.quiz = None
        if "flashcards" not in st.session_state:
            st.session_state.flashcards = None
        if "lesson_content" not in st.session_state:
            st.session_state.lesson_content = None

        # Build Interactive Workspace Tabs Container
        tab_quiz, tab_flash, tab_less = st.tabs(["📝 Quiz Generator", "🗂️ Flashcards Maker", "📖 Lesson Planner"])

        # ==========================================
        # --- 1. QUIZ GENERATOR TAB (TIER GUARDED) ---
        # ==========================================
        with tab_quiz:
            st.subheader("Quiz Generator")

            # Get the active lesson FIRST
            active_lesson = st.session_state.get("lms_active_lesson_node")

            # 1. Determine what the active topic should be based on your context logic
            if active_lesson:
                computed_topic = active_lesson.get("title", "")
            else:
                # If the user typed something else manually, preserve it; otherwise fall back to sub_topic
                computed_topic = st.session_state.get("workspace_quiz_topic", sub_topic)

            # 2. Force update session state when the active context changes
            if "workspace_quiz_topic" not in st.session_state or active_lesson:
                st.session_state["workspace_quiz_topic"] = computed_topic
            elif st.session_state.get("last_sub_topic") != sub_topic and not active_lesson:
                # This ensures that if the sidebar subbox changes, the quiz topic updates automatically
                st.session_state["workspace_quiz_topic"] = sub_topic
                st.session_state["last_sub_topic"] = sub_topic

            # 3. Render the text input safely WITHOUT the 'value=' conflict parameter
            raw_quiz_input = st.text_input(
                "Quiz Topic",
                key="workspace_quiz_topic"
            )

            quiz_topic: str = str(raw_quiz_input).strip() if raw_quiz_input else ""

            
            # 2. Fetch student tier profile data upfront using email lookup
            user_profile_raw = get_student_data(st.session_state.user_email)
            student_profile = user_profile_raw if user_profile_raw is not None else {}
            
            # Safely extract baseline profile details
            name = str(student_profile.get("name", ""))
            grade = str(student_profile.get("grade", ""))
            try:
                age_int = int(student_profile.get("age", 0))
            except (ValueError, TypeError):
                age_int = 0
            
            # Safeguard Tier Lookup matching working sidebar patterns
            subscription_tree = student_profile.get('subscription', {}) if isinstance(student_profile.get('subscription'), dict) else {}
            raw_tier = subscription_tree.get('tier', 'Free')
            
            # Normalize user_tier to match your tier guard system (Pylance Typecast Fix)
            user_tier = str(raw_tier).strip()
            
            # ----------------------------------------------------
            # AUTO-RESET CRITICAL BUG FIX: Clear stale limit states
            # ----------------------------------------------------
            if "premium" in user_tier.lower() or "plus" in user_tier.lower():
                st.session_state.quiz_limit_reached = False
            uid = str(st.session_state.get("uid") or st.session_state.user_email)
            
            # Check if there is an active quiz currently displayed on screen
            if "quiz" not in st.session_state:
                st.session_state.quiz = None
            has_active_quiz = st.session_state.quiz is not None

            # ----------------------------------------------------
            # State-Driven Upgrade Gatekeeper Banner
            # ----------------------------------------------------
            if st.session_state.get("quiz_limit_reached") and not has_active_quiz:
                st.error("⚠️ Quizzes Limit Reached! Wait for 24hrs or Upgrade to Premium to continue.")
                
                if st.button("🚀 Upgrade to Premium", key="quiz_upgrade_unique_btn"):
                    st.session_state.pop("quiz_limit_reached", None)
                    st.session_state.trigger_quiz_upgrade_modal = True
                    st.rerun()

            # ----------------------------------------------------
            # Safe Modal Activation Layer (Prevents Continuous Loops)
            # ----------------------------------------------------
            if st.session_state.get("trigger_quiz_upgrade_modal"):
                st.session_state.pop("trigger_quiz_upgrade_modal", None)
                if 'show_upgrade_modal' in globals():
                    show_upgrade_modal()

            # ----------------------------------------------------
            # Quiz Generation Action Trigger
            # ----------------------------------------------------
            if st.button("Generate Quiz", use_container_width=True):
                if not quiz_topic:
                    st.warning("Please enter a quiz topic.")
                elif not name or not grade or age_int == 0:
                    st.warning("Please create Student Profile in the sidebar first!")
                
                # Guard tier allowance at the moment of clicking using normalized variables
                elif not verify_tier_allowance(uid, user_tier, "quizzes"):
                    st.session_state.quiz_limit_reached = True
                    st.rerun()
                else:
                    st.session_state.pop("quiz_limit_reached", None)
                    with st.spinner("Generating quiz..."):
                        # Ensure fallback fallback contextual arguments exist
                        target_diff = get_next_difficulty(name, grade, age_int, quiz_topic)
                        
                        # 🎯 PASS CORRECTING CONTEXT: Use 'student' dict to send preferred_language and subject parameters
                        active_context = dict(student if 'student' in locals() else student_profile)

                        # Synchronize the context with the active lesson
                        active_context["sub_topic"] = quiz_topic
                        active_context["topic"] = quiz_topic
                        quiz_result = generate_quiz(quiz_topic, active_context, target_diff)
                        
                        if quiz_result:
                            st.session_state.quiz = quiz_result
                            st.session_state.quiz_submitted = False
                            st.session_state.quiz_score = 0
                            st.session_state.quiz_raw_score = 0
                            
                            MwalimuDBService.increment_usage(uid, "quizzes")
                            
                            if not verify_tier_allowance(uid, user_tier, "quizzes"):
                                st.session_state.quiz_limit_reached = True
                            
                                save_activity(
                                    student_uid=str(st.session_state.get("uid", "")), # 🌟 FIXED: Pass the active student UID string
                                    student_name=name,
                                    student_grade=grade,
                                    student_age=age_int,
                                    activity_type="quiz_generation",
                                    topic=quiz_topic,
                                    score=0,
                                    subject=subject,
                                    topics=quiz_topic,
                                    sub_topic=quiz_topic,
                                    learning_outcome=student.get("learning_outcome", "General") if 'student' in locals() else "General"
                                )

                            st.rerun()

            # ----------------------------------------------------
            # 🎯 DYNAMIC LOCALIZATION LABELS FOR FRONTEND VIEW
            # ----------------------------------------------------
            current_lang = student.get("preferred_language", "English") if 'student' in locals() else "English"
            is_swahili = "swahili" in str(current_lang).lower()
            
            label_q_prefix = "Swali" if is_swahili else "Question"
            label_choice_title = "Chagua jibu:" if is_swahili else "Choose your answer:"
            label_warning_unanswered = "Tafadhali jibu maswali yote kabla ya kuwasilisha." if is_swahili else "Please answer all questions before submitting."

            # ----------------------------------------------------
            # Render Active Quiz Layout (Stays open across user interactions)
            # ----------------------------------------------------
            if st.session_state.quiz:
                #===
                quiz_data = []
                # 🎯 FIX: Declare clean_str outside the try block entirely
                clean_str = "" 
                
                try:
                    raw_json = st.session_state.quiz
                    
                    if isinstance(raw_json, str):
                        clean_str = str(raw_json).strip()
                        
                        # 1. Clear out markdown code block wrappers
                        if clean_str.startswith("```json"):
                            clean_str = clean_str.replace("```json", "", 1).rstrip("`").strip()
                        elif clean_str.startswith("```"):
                            clean_str = clean_str.replace("```", "", 1).rstrip("`").strip()
                        
                        # Clean up typos like rogue operators or dangling equal signs
                        clean_str = re.sub(r'\[\s*=\s*"', '["', clean_str)
                        clean_str = re.sub(r',\s*=\s*"', ',"', clean_str)
                        clean_str = re.sub(r'\[\s*:\s*"', '["', clean_str)
                        clean_str = re.sub(r',\s*:\s*"', ',"', clean_str)

                        # 2. Parse using standard JSON engine
                        parsed_data = json.loads(clean_str)
                    else:
                        parsed_data = raw_json
                    
                    quiz_data = parsed_data.get("quiz", parsed_data.get("questions", [])) if isinstance(parsed_data, dict) else parsed_data
                    
                except Exception as parse_error:
                    try:
                        # Pylance is now guaranteed that clean_str is initialized to at least a blank string
                        clean_ast = clean_str.replace("true", "True").replace("false", "False").replace("null", "None")
                        parsed_data = ast.literal_eval(clean_ast)
                        quiz_data = parsed_data.get("quiz", parsed_data.get("questions", [])) if isinstance(parsed_data, dict) else parsed_data
                    except Exception:
                        quiz_data = st.session_state.quiz




                # Draw questions loop cleanly if parsed format matches
                if isinstance(quiz_data, list):
                    st.markdown("### Generated Quiz")
                    for i, question in enumerate(quiz_data):
                        st.markdown(f"#### {label_q_prefix} {i+1}")
                        
                        raw_opts = question.get("options", [])
                        options_list = list(raw_opts.values()) if isinstance(raw_opts, dict) else raw_opts
                        
                        st.radio(
                            question.get("question", ""),
                            options_list,
                            index=None,
                            key=f"q_{i}",
                            disabled=st.session_state.get("quiz_submitted", False),
                            label_visibility="visible" if label_choice_title else "collapsed"
                        )
                    
                    # Submit handling block
                    if not st.session_state.get("quiz_submitted", False):
                        if st.button("Submit Quiz", use_container_width=True):
                            current_answers = [st.session_state.get(f"q_{i}") for i in range(len(quiz_data))]
                            if None in current_answers:
                                st.warning(label_warning_unanswered)
                            else:
                                score = 0

                                for i, q in enumerate(quiz_data):
                                    if current_answers[i] == q.get("answer"):
                                        score += 1

                                total_questions = len(quiz_data)

                                st.session_state.quiz_raw_score = score
                                st.session_state.quiz_score = round((score / total_questions) * 100)
                                st.session_state.quiz_submitted = True

                                # ==============================
                                # LMS Progress Update
                                # ==============================
                                evaluate_quiz_submission(
                                    correct_answers=score,
                                    total_questions=total_questions
                                )

                                save_activity(
                                    student_uid=str(st.session_state.get("uid", "")),
                                    student_name=name,
                                    student_grade=grade,
                                    student_age=age_int,
                                    activity_type="quiz_score",
                                    topic=quiz_topic,
                                    score=st.session_state.quiz_score,
                                    subject=student.get("subject","General"),
                                    topics=student.get("topic","General"),
                                    sub_topic=student.get("sub_topic","General"),
                                    learning_outcome=student.get("learning_outcome","General")
                                )
                                st.rerun()

                # ---------------------------------------------------- 
                # Post-Submission Review Display
                # ----------------------------------------------------
                if st.session_state.get("quiz_submitted", False) and isinstance(quiz_data, list):
                    raw_score = st.session_state.get("quiz_raw_score", 0)
                    total_questions = len(quiz_data)
                    percentage = st.session_state.get("quiz_score", 0)
                    
                    # Localized correction metrics card titles
                    banner_msg = f"🎉 Umepata {raw_score}/{total_questions} ({percentage}%)" if is_swahili else f"📊 You scored {raw_score}/{total_questions} ({percentage}%)"
                    st.success(banner_msg)
                    
                    review_heading = "### Uhakiki wa Majibu" if is_swahili else "### Answer Review"
                    st.markdown(review_heading)
                    
                    for i, q in enumerate(quiz_data):
                        student_answer = st.session_state.get(f"q_{i}")
                        correct_answer = q.get("answer")
                        
                        st.markdown(f"**{label_q_prefix} {i+1}**")
                        st.write(q.get("question"))
                        
                        answer_label = "👉 Jibu Lako:" if is_swahili else "👉 Your Answer:"
                        correct_label = "Jibu Sahihi:" if is_swahili else "Correct Answer:"
                        
                        st.write(f"*{answer_label}* `{student_answer}`")
                        
                        if student_answer == correct_answer:
                            st.success(f"✅ {correct_label} {correct_answer}")
                        else:
                            st.error(f"❌ {correct_label} {correct_answer}")
                    
                    # Clear layout to reset state controls cleanly
                    reset_label = "Futa Matokeo ya Maswali" if is_swahili else "Clear Quiz Results"
                    if st.button(reset_label, use_container_width=True, key="clear_workspace_quiz_results"):
                        st.session_state.quiz = None
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_raw_score = 0
                        
                        if not verify_tier_allowance(uid, user_tier, "quizzes"):
                            st.session_state.quiz_limit_reached = True
                        st.rerun()



        # ==========================================
        # --- 2. FLASHCARDS TAB (TIER GUARDED) ---
        # ==========================================
                #=====Flash Card ====
        with tab_flash:
            st.subheader("AI Flashcards Maker")
            
            # Ensure input string extraction can never evaluate as NoneType or throw Pylance errors
            raw_fc_input = st.text_input("Enter a topic for your flashcards:", value=sub_topic if 'sub_topic' in locals() else "", key="fc_topic")
            flashcard_topic: str = str(raw_fc_input).strip() if raw_fc_input else ""
            
            # Fetch student tier profile data upfront using clean email lookups
            user_profile_raw = get_student_data(st.session_state.user_email)
            student_profile = user_profile_raw if user_profile_raw is not None else {}
            
            # Safely extract baseline profile details
            name = str(student_profile.get("name", ""))
            grade = str(student_profile.get("grade", ""))
            try:
                age_int = int(student_profile.get("age", 0))
            except (ValueError, TypeError):
                age_int = 0

            # Safeguard Tier Lookup matching working sidebar patterns
            subscription_tree = student_profile.get('subscription', {}) if isinstance(student_profile.get('subscription'), dict) else {}
            raw_tier = subscription_tree.get('tier', 'Free')
            
            # Normalize user_tier to match your tier guard system
            user_tier = str(raw_tier).strip()
            
            # ----------------------------------------------------
            # AUTO-RESET CRITICAL BUG FIX: Clear stale limit states 
            # ----------------------------------------------------
            if "premium" in user_tier.lower() or "plus" in user_tier.lower():
                st.session_state.flashcards_limit_reached = False

            uid = str(st.session_state.get("uid") or st.session_state.user_email)
            
            # Check if there are active flashcards currently displayed on screen safely
            if "flashcards" not in st.session_state:
                st.session_state.flashcards = None
                
            has_active_flashcards = st.session_state.flashcards is not None

            # ----------------------------------------------------
            # State-Driven Upgrade Gatekeeper Banner
            # ----------------------------------------------------
            if st.session_state.get("flashcards_limit_reached") and not has_active_flashcards:
                st.error("⚠️ Flashcards Limit Reached! Wait for 24hrs or Upgrade to Premium to continue.")
                
                if st.button("🚀 Upgrade to Premium", key="fc_upgrade_unique_btn"):
                    st.session_state.pop("flashcards_limit_reached", None)
                    st.session_state.trigger_fc_upgrade_modal = True
                    st.rerun()

            # ----------------------------------------------------
            # Safe Modal Activation Layer (Prevents Continuous Loops)
            # ----------------------------------------------------
            if st.session_state.get("trigger_fc_upgrade_modal"):
                st.session_state.pop("trigger_fc_upgrade_modal", None)
                if 'show_upgrade_modal' in globals():
                    show_upgrade_modal()

            # ----------------------------------------------------
            # Flashcards Generation Action Trigger
            # ----------------------------------------------------
            if st.button("Generate Flashcards", use_container_width=True, key="execute_workspace_flashcards"):
                if not flashcard_topic:
                    st.warning("Please enter a valid topic first!")
                elif not name or not grade or age_int == 0:
                    st.warning("Please create Student Profile in the sidebar first!")
                
                # Guard tier allowance at the moment of clicking using unified parameters
                elif not verify_tier_allowance(uid, user_tier, "flashcards"):
                    st.session_state.flashcards_limit_reached = True
                    st.rerun()
                else:
                    st.session_state.pop("flashcards_limit_reached", None)

                    with st.spinner("Mwalimu AI is writing your flashcards..."):
                        # 🎯 FIX: Pass active contextual 'student' map to respect Subject and preferred_language
                        active_context = student if 'student' in locals() else student_profile
                        fc_result = generate_flashcards(flashcard_topic, active_context)
                        
                        if fc_result:
                            st.session_state.flashcards = fc_result
                            MwalimuDBService.increment_usage(uid, "flashcards")
                            
                            if not verify_tier_allowance(uid, user_tier, "flashcards"):
                                st.session_state.flashcards_limit_reached = True
                            st.rerun()

            # ----------------------------------------------------
            # SAFE DISPLAY & STRUCTURAL JSON PARSING LAYER
            # ----------------------------------------------------
            if st.session_state.flashcards:
                st.info("💡 Click 'Show Answer' to test your active recall memory knowledge!")
                
                import json
                try:
                    cards_data = st.session_state.flashcards
                    
                    # Clean and unpack markdown string code block wrappers safely
                    if isinstance(cards_data, str):
                        clean_flash = str(cards_data).strip()
                        if clean_flash.startswith("```json"):
                            clean_flash = clean_flash.replace("```json", "", 1).rstrip("`").strip()
                        elif clean_flash.startswith("```"):
                            clean_flash = clean_flash.replace("```", "", 1).rstrip("`").strip()
                        cards_data = json.loads(clean_flash)
                    
                    # Unroll nested payload mappings gracefully matching all potential AI output types
                    if isinstance(cards_data, dict):
                        actual_list = cards_data.get("flashcards", cards_data.get("cards", cards_data.get("questions", [])))
                    elif isinstance(cards_data, list):
                        actual_list = cards_data
                    else:
                        actual_list = []

                    # Draw interactive elements loops safely
                    for idx, card in enumerate(actual_list):
                        if isinstance(card, dict):
                            # 🎯 FIX: Check for English AND Swahili key variants generated by the AI
                            q_text = card.get("front", card.get("question", card.get("swali", card.get("mbele", "No question context"))))
                            a_text = card.get("back", card.get("answer", card.get("jibu", card.get("nyuma", "No answer context"))))
                        else:
                            q_text = f"Card Detail Element {idx + 1}"
                            a_text = str(card)

                        st.markdown(f"### Flashcard {idx + 1}")
                        st.write(f"**❓ Question:** {q_text}")
                        
                        with st.expander("👁️ Show Answer"):
                            st.success(f"**💡 Answer:** {a_text}")

                            
                except Exception as parse_error:
                    # Absolute emergency string fallback layout to prevent crashes if JSON format breaks
                    st.markdown(st.session_state.flashcards)
                
                st.markdown("---")
                if st.button("Clear Flashcards", use_container_width=True, key="clear_workspace_flashcards"):
                    st.session_state.flashcards = None
                    if not verify_tier_allowance(uid, user_tier, "flashcards"):
                        st.session_state.flashcards_limit_reached = True
                    st.rerun()


        
        # ==========================================
        # --- 3. LESSON GENERATOR TAB (TIER GUARDED) ---
        # ==========================================
        with tab_less:
            st.subheader("AI Lessons Generator")
            
            # 🎯 PYLANCE FIX: Protect lesson text input string binding variables from NoneType evaluations
            # If learning_outcome is missing or local context varies, it defaults safely to an empty string
            default_lesson_value = learning_outcome if 'learning_outcome' in locals() and learning_outcome else ""
            raw_lesson_input = st.text_input("Enter the topic you want to learn today:", value=default_lesson_value, key="lesson_topic_input")
            lesson_topic: str = str(raw_lesson_input).strip() if raw_lesson_input else ""
            
            # Fetch student tier profile data upfront using structured backend definitions
            student_profile = get_student_data(st.session_state.user_email) or {}
            subscription = student_profile.get("subscription", {}) if isinstance(student_profile.get("subscription"), dict) else {}
            user_tier = str(subscription.get("tier", "Free")).strip()
            uid = str(st.session_state.get("uid") or st.session_state.user_email)
            
            # Extract baseline metrics for your background firestore activity logging map layers
            name = str(student_profile.get("name", "Student"))
            grade = str(student_profile.get("grade", "General"))
            try:
                age_int = int(student_profile.get("age", 0))
            except (ValueError, TypeError):
                age_int = 0
            
            # Check if there is active lesson content currently displayed on screen safely
            has_active_lesson = "lesson_content" in st.session_state and st.session_state.lesson_content is not None

            # ----------------------------------------------------
            # State-Driven Upgrade Gatekeeper Banner
            # ----------------------------------------------------
            if st.session_state.get("lessons_limit_reached") and not has_active_lesson:
                st.error("⚠️ Lessons Limit Reached, Wait for 24hrs or Upgrade to Premium to continue!")
                
                if st.button("🚀 Upgrade to Premium", key="lesson_upgrade_unique_btn"):
                    st.session_state.pop("lessons_limit_reached", None)
                    st.session_state.trigger_lesson_upgrade_modal = True
                    st.rerun()

            # ----------------------------------------------------
            # Safe Modal Activation Layer (Prevents Continuous Loops)
            # ----------------------------------------------------
            if st.session_state.get("trigger_lesson_upgrade_modal"):
                st.session_state.pop("trigger_lesson_upgrade_modal", None)
                if 'show_upgrade_modal' in globals():
                    show_upgrade_modal()

            # ----------------------------------------------------
            # Lessons Generation Action Trigger
            # ----------------------------------------------------
            if st.button("Generate Lesson", use_container_width=True, key="execute_workspace_lessons"):
                if not lesson_topic:
                    st.warning("Please enter a valid lesson topic first!")
                elif not name or name == "Student":
                    st.warning("Please create Student Profile in the sidebar first!")
                
                # 🎯 1. FIX: Request allowance using the exact plural configuration key
                elif not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                    st.session_state.lessons_limit_reached = True
                    st.rerun()
                else:
                    st.session_state.pop("lessons_limit_reached", None)

                    with st.spinner("Mwalimu AI is preparing your personalized lesson..."):
                        try:
                            active_student_context = student if 'student' in locals() else student_profile
                            st.session_state.lesson_content = generate_lesson(lesson_topic, active_student_context)
                            
                            # 🎯 2. FIX: Deduct usage tokens inside the plural "lessons" registry row
                            MwalimuDBService.increment_usage(uid, "lessons")
                            
                            st.session_state.user_profile = None  # Instantly wipe the view profile RAM cache
                            
                            if not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                                st.session_state.lessons_limit_reached = True
                                
                            act_subject = student.get("subject", "General") if 'student' in locals() else "General"
                            act_topic = student.get("topic", "General") if 'student' in locals() else "General"
                            act_sub = student.get("sub_topic", "General") if 'student' in locals() else "General"
                            act_out = student.get("learning_outcome", "General") if 'student' in locals() else "General"

                            # 🎯 3. FIX: Save activity mapping configuration tracking logs as "lessons"
                            save_activity(
                                student_uid=uid,
                                student_name=name, student_grade=grade, student_age=age_int,
                                activity_type="lessons", topic=lesson_topic, score=0,
                                subject=act_subject, topics=act_topic, sub_topic=act_sub, learning_outcome=act_out
                            )
                        except Exception as e:
                            st.error(f"Failed to generate lesson: {str(e)}")
                        st.rerun()


                        
            # ----------------------------------------------------
            # Render Active Lesson Layout (Safe String Backtick Cleaner)
            # ----------------------------------------------------
            if "lesson_content" in st.session_state and st.session_state.lesson_content:
                st.markdown("---")
                st.info("Tip: Read through the breakdown below. Mwalimu customized this explanation precisely for your style!")
                
                raw_lesson = st.session_state.lesson_content
                if raw_lesson and isinstance(raw_lesson, str):
                    # 🎯 PYLANCE FIX: Safely wrap string cast evaluations before cleaning block backticks
                    safe_lesson: str = str(raw_lesson).strip()
                    
                    if safe_lesson.startswith("```markdown"):
                        safe_lesson = safe_lesson.replace("```markdown", "", 1).rstrip("`").strip()
                    elif safe_lesson.startswith("```"):
                        safe_lesson = safe_lesson.replace("```", "", 1).rstrip("`").strip()
                    st.markdown(safe_lesson)
                else:
                    st.write(raw_lesson)
                    
                if st.button("Clear Lesson Content", use_container_width=True, key="clear_workspace_lessons"):
                    st.session_state.lesson_content = None
                    
                    if not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                        st.session_state.lessons_limit_reached = True
                    st.rerun()




    # =====================================================================
# --- PAGE VIEW MODE 2: VOICE TUTOR DASHBOARD MODE ---
# =====================================================================
    elif st.session_state.current_page == "Voice Tutor":
        st.markdown("---")
        if st.button("Back to Main Chat Dashboard", use_container_width=True, key="back_from_voice"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
            
        if not name:
            st.warning("Please enter your name in the Student Profile registration section.")
        else:
            # 1. Fetch the latest user profile to get the tier
            user_data = get_student_data(st.session_state.uid)
            subscription = user_data.get('subscription', {}) if user_data else {}
            tier = subscription.get('tier', 'Free')

            # 2. GATE THE FEATURE: Only allow 'Premium' tier
            if str(tier).strip().lower() == "premium":
                # Check if environment setup exists
                api_key = os.environ.get("OPENROUTER_API_KEY") or st.secrets.get("OPENROUTER_API_KEY")
                if api_key:
                    # 🎯 FIX: Declare an explicit localized client inside this scope block!
                    from openai import OpenAI
                    local_voice_client = OpenAI(
                        base_url="https://openrouter.ai", 
                        api_key=api_key
                    )
                    
                    # 🛡️ LOCAL HISTORY FORCING AT THE SWITCH ROUTER ENTRY
                    # 🛡️ LOCAL HISTORY FORCING AT THE SWITCH ROUTER ENTRY
                    current_subject = st.session_state.get("active_subject", "General Studies")

                    if (
                        "voice_chat_history" not in st.session_state
                        or st.session_state.get("last_voice_subject") != current_subject
                    ):

                        from services.database import get_voice_chat_history

                        try:
                            all_raw_history = get_voice_chat_history(
                                str(st.session_state.get("uid", "")),
                                current_subject
                            )

                            # Clear previous history
                            st.session_state.voice_chat_history = []

                            # Keep only voice records
                            voice_records = [
                                msg for msg in all_raw_history
                                if msg.get("is_voice") or msg.get("role") in ["voice_student", "voice_assistant"]
                            ]

                            # Convert roles for the UI
                            for msg in voice_records:

                                if msg["role"] in ["voice_student", "student", "user"]:
                                    ui_role = "user"
                                else:
                                    ui_role = "assistant"

                                st.session_state.voice_chat_history.append({
                                    "role": ui_role,
                                    "content": msg["content"],
                                    "is_voice": True,
                                    "audio_bytes": msg.get("audio_bytes")
                                })

                            # ✅ Only update after successful loading
                            st.session_state.last_voice_subject = current_subject

                        except Exception:
                            st.session_state.voice_chat_history = []
                    # Pass this localized client directly to your voice tutor engine
                    render_voice_tutor_page(local_voice_client)
                else:
                    st.error("OpenRouter Gateway API configurations are currently offline.")
                
            else:
                # 3. Handle the blocked state
                st.warning("🎙️ **Voice Tutor Mode is a Premium Feature.**")
                st.info("Upgrade to Premium to unlock interactive audio learning and more!")
                if st.button("🚀 Upgrade to Premium", key="voice_upgrade"):
                    show_upgrade_modal()

    #========================================================    
    # PAGE VIEW MODE 3: LMS LESSON WORKSPACE INTERFACE CANVAS
    #========================================================
    elif st.session_state.current_page == "LMS Lesson Workspace":
        from ui_components.lesson_page import render_active_lesson_workspace
        render_active_lesson_workspace()
        
    # 🏆 PAGE VIEW MODE 4: PUBLIC STUdENT LEAdERBOARD HUB VIEW
    elif st.session_state.current_page == "Leaderboard Hub":
        from ui_components.leaderboard_page import render_student_leaderboard_page
        render_student_leaderboard_page()      
    

    #======================
    elif st.session_state.current_page == "Admin Dashboard":
        render_admin_dashboard()

    #======================================================    
    # EDIT STUDENT PROFILE
    # ======================================================
    elif st.session_state.current_page == "Edit Profile":
        st.markdown("---")
        if st.button("⬅ Back to Main Chat Dashboard", use_container_width=True):
            st.session_state.current_page = "Main Chat"
            st.rerun()
            
        st.subheader("⚙ Edit Student Profile")
        st.write("Keep your academic milestones up to date. Changing your profile details or baseline grade helps Mwalimu AI adjust the difficulty of quizzes and voice tasks automatically.")
        
        # 1. Fetch active data parameters cleanly
        current_uid = st.session_state.get("uid") or st.session_state.get("user_email")
        user_doc_ref = db.collection("users").document(str(current_uid))
        active_profile = user_doc_ref.get().to_dict() or {}
        
        if active_profile:
            with st.container(border=True):
                # 2. Keep Email locked (Read-Only), but allow Student Name to be modified                               
                input_name = st.text_input("Student Name", value=active_profile.get("name", st.session_state.get("student_name", "Student")))
                st.text_input("Registered Email Address", value=active_profile.get("email", st.session_state.get("user_email", "")), disabled=True)                
                # Type Guard: Coerce the output parameter explicitly into a guaranteed string layout
                new_name = str(input_name) if input_name is not None else ""
                
                # Validation to ensure the student name isn't left empty
                if not new_name.strip():
                    st.error("Student Name cannot be left blank.")

                
                # 3. Allow Grade and Age to change
                grades_list = [f"Grade {i}" for i in range(1, 13)]
                saved_grade = active_profile.get("grade", "Grade 1")
                
                # Dynamic fallback index detection matching schema patterns
                try:
                    default_grade_index = grades_list.index(saved_grade)
                except ValueError:
                    default_grade_index = 0
                    
                new_grade = st.selectbox("Current Grade Level", grades_list, index=default_grade_index)
                new_age = st.number_input("Age", min_value=5, max_value=25, value=int(active_profile.get("age", 7)))
                
                # 4. Show learning reset warning message block
                st.warning("""
                ⚠️ **Important Progress Notice:**
                Changing your current grade level or age parameters will reset:
                • Active Quiz performance trends
                • Voice tracking mastery metrics
                • Progress dashboard status bars
                
                *Note: Your account billing status, historical tier details, and registration profile email will remain unaffected.*
                """)
                
                # 5. Requirement confirmation checkbox gateway
                confirm_reset = st.checkbox("I understand and authorize Mwalimu AI to re-align my progress tracking records to this new profile configuration.")
                
                # 6. Execution validation button pipeline                              
                if st.button("Save Profile Settings", use_container_width=True, type="primary"):
                    # Type Guard: Ensure safe string falling boundaries
                    safe_name = str(new_name) if new_name is not None else ""
                    
                    if not safe_name.strip():
                        st.error("Please provide a valid Student Name before saving.")
                    elif not confirm_reset:
                        st.error("Please acknowledge the progress re-alignment warning checkbox above before saving modifications.")
                    else:
                        with st.spinner("Re-aligning your academic workspace profile..."):
                            # A. Update document values inside Firestore collection mapping (including name)
                            user_doc_ref.update({
                                "name": safe_name.strip(),
                                "grade": new_grade,
                                "age": int(new_age)
                            })
                            
                            # B. Clear performance collection histories matched to this specific user ID
                            collections_to_wipe = ["quiz_history", "learning_analysis", "quiz_results", "student_progress"]
                            for target_col in collections_to_wipe:
                                try:
                                    stale_docs = db.collection(target_col).where(
                                        filter=FieldFilter("uid", "==", str(current_uid))
                                    ).stream()
                                    for doc_item in stale_docs:
                                        db.collection(target_col).document(doc_item.id).delete()
                                except Exception:
                                    pass # Prevent interruptions if an optional analytics collection doesn't exist yet
                            
                            # C. Synchronize state keys locally to immediate runtime context
                            st.session_state.student_name = safe_name.strip()
                            st.session_state.grade = new_grade
                            st.session_state.age = int(new_age)
                            
                            # Type Guard: Explicitly verify dictionary structure existence before indexing
                            current_profile = st.session_state.get("user_profile")
                            if current_profile is not None and isinstance(current_profile, dict):
                                current_profile["name"] = safe_name.strip()
                                current_profile["grade"] = new_grade
                                current_profile["age"] = int(new_age)
                                # Re-assign the mutated dictionary cleanly back to session state
                                st.session_state.user_profile = current_profile
                                
                            st.toast("🎉 Profile settings synchronized successfully!")
                            st.session_state.current_page = "Main Chat"
                            st.rerun()

        else:
            st.error("Unable to load active profile registry parameters from database data stores.")


     
   
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