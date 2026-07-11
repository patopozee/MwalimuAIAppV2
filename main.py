import base64
import os
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
import requests
import streamlit.components.v1 as components
from services.auth_service import MwalimuAuthService
from services.payment_service import MpesaPaymentService
from services.tier_guard import verify_tier_allowance
from services.ai import ask_mwalimu, generate_quiz, generate_study_plan, generate_flashcards, generate_lesson
from services.db_service import MwalimuDBService
from services.ui_components import show_upgrade_modal
from services.database import get_student_data, get_student_stats
from services.legal_text import TERMS_AND_CONDITIONS
import json
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Initialize Firebase Admin SDK (Only if it hasn't been initialized yet)
if not firebase_admin._apps:
    # Option A: If you are using the service account string from st.secrets
    try:
        secret_json = json.loads(st.secrets["firebase"]["service_account_json"])
        cred = credentials.Certificate(secret_json)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Failed to initialize Firebase credentials: {e}")

# 2. Define 'db' globally so line 130 can access it 🌟
db = firestore.client()
# ==DATABASE CALL CODE==
from services.database import (
    create_tables,
    save_activity,
    get_student_stats,
    get_student_quiz_history,
    get_next_difficulty,
    get_student_learning_analysis,
    get_chat_history,
    save_chat_message,
    clear_student_chat_history,
    get_student_data
)
from voice_page import render_voice_tutor_page
from config import CBC  # Dynamic CBC repository dictionary
import streamlit as st
if st.get_option("server.port") == 8501:
    # We are running locally on our machine
    REDIRECT_URI = "http://localhost:8501"
else:
    # We are deployed live on Streamlit Community Cloud
    # Replace this string with your EXACT live Streamlit application URL
    REDIRECT_URI = "https://mwalimuaiappv2.streamlit.app" 

# --- STREAMLIT PAGE CONFIGURATION (MUST BE ABSOLUTE FIRST COMMAND)
st.set_page_config(
    page_title="Mwalimu AI App",
    page_icon="assets/logo112.png",
    layout="wide",
    initial_sidebar_state="expanded"
    
)

# INITIALIZATION
load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
create_tables()

# --- INITIALIZE STATE WORKSPACE ---
if "user_authenticated" not in st.session_state: st.session_state.user_authenticated = False
if "messages" not in st.session_state: st.session_state.messages = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "Main Chat"
if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []
if "quiz_raw_score" not in st.session_state:
    st.session_state.quiz_raw_score = 0
if "quiz_score" not in st.session_state:
    st.session_state.quiz_score = 0
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "study_plan" not in st.session_state:
    st.session_state.study_plan = None
if "flashcards" not in st.session_state:
    st.session_state.flashcards = []
if "lesson_content" not in st.session_state:
    st.session_state.lesson_content = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_profile" not in st.session_state:
    st.session_state.user_profile = None
if "student_name" not in st.session_state:
    st.session_state.student_name = ""

# 🚀 TOP-LEVEL GOOGLE OAUTH INTERCEPTOR
if "code" in st.query_params and not st.session_state.user_authenticated:
    auth_code = st.query_params["code"]
    try:
        cid = st.secrets["google_oauth"]["client_id"]
        csecret = st.secrets["google_oauth"]["client_secret"]
        
        token_url = "https://oauth2.googleapis.com/token"
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
        
        # 🌟 Check if Google accepted the transaction before decoding JSON
        if response.status_code == 200:
            token_response = response.json()
            
            if "access_token" in token_response:
                user_info = requests.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={
                        "Authorization": f"Bearer {token_response['access_token']}"
                    },
                ).json()
                
                # Extract clean string parameters safely
                google_uid = user_info.get("id") or user_info.get("sub")
                email_val = user_info.get("email", "").strip().lower()
                name_val = user_info.get("name", "Student").strip().title()
                
                if not google_uid:
                    st.error("Authentication failed: Missing unique user ID from Google.")
                    st.stop()
                
                # Check if the document already exists in the database BEFORE writing anything
                                # Check if the document already exists in the database BEFORE writing anything
                check_doc = db.collection("users").document(google_uid).get()
                
                # 🌟 STEP 1: MOVE THIS OUTSIDE AND ABOVE THE IF BLOCK
                # Define baseline dictionary payload matching your Firestore schema exactly
                user_profile_payload = {
                    "uid": google_uid,
                    "name": name_val,
                    "email": email_val,
                    "grade": "Grade 6", # Default fallback parameter
                    "age": 12,          # Default fallback parameter
                    "created_at": "2026-07-11T13:08:00Z", # Current ISO timestamp
                    "subscription": {
                        "tier": "Free",
                        "payment_status": "Pending",
                        "reference_id": "",
                        "expiry_date": ""
                    }
                }
                
                # 🌟 STEP 2: KEEP YOUR CHECK LOCK (It now safely reads the payload above it)
                # Only create baseline profiles for completely NEW signups
                if not check_doc.exists:
                    # WRITE DIRECTLY TO CLOUD FIRESTORE FOR FIRST-TIME SIGNUPS ONLY
                    db.collection("users").document(google_uid).set(user_profile_payload, merge=True)
                
                # Fetch fresh payload back from DB to respect existing parameters
                                # Fetch fresh payload back from DB to respect existing parameters
                fresh_doc = db.collection("users").document(google_uid).get()
                doc_data = fresh_doc.to_dict()
                final_data = doc_data if (fresh_doc.exists and doc_data is not None) else user_profile_payload
                
                # 🌟 STEP 1: FORCE THE CORE ROUTING PARAMETERS TO MATCH EMAIL LOGIN EXACTLY
                st.session_state.user_authenticated = True
                st.session_state.uid = google_uid
                st.session_state.user_email = final_data.get("email", email_val)
                st.session_state.student_name = final_data.get("name", name_val)
                
                # Populate component parameters directly from your Firestore data fields
                st.session_state.grade = final_data.get("grade", "Grade 6")
                st.session_state.age = int(final_data.get("age", 12))
                st.session_state.user_profile = final_data
                
                # Clear the query code from the URL bar to prevent infinite reload loops
                st.query_params.clear()
                st.toast(f"🎉 Welcome back, {st.session_state.student_name}!")
                
                # 🌟 STEP 2: REMOVED REDUNDANT INITIALIZE LOCK TO PREVENT LOGOUT SQUASH
                
                
                # Fire the rerun trigger to switch views into the Main Workspace Dashboard
                st.rerun()

            
    except Exception as e:
        st.error(f"Authentication background sync failed: {str(e)}")





# ADD THE CSS BLOCK HERE (Right after page config)
st.html(f"""
    <style>
    @media (min-width: 768px) {{
    [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
    [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: 1.5rem !important; padding-top: 0rem !important; }}
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
                                # FIXED: Success box prints safely here, and state changes only when they click back
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
                # Safe execution line: get_base64_image is now fully recognized!
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
    #user_data = get_student_data(st.session_state.user_email)

    # === SIDEBAR ACCOUNT CONFIGURATION ===
    raw_name = st.sidebar.text_input("Student Name", value=st.session_state.get("student_name") or "")
    name = raw_name.strip().title() if raw_name else ""
    grades = [
            "Grade 1", "Grade 2", "Grade 3", "Grade 4",
            "Grade 5", "Grade 6", "Grade 7", "Grade 8",
            "Grade 9", "Grade 10", "Grade 11", "Grade 12"
        ]

    current_grade = st.session_state.get("grade", "Grade 1")

    # Safety check in case the stored grade isn't in the list
    if current_grade not in grades:
        current_grade = "Grade 1"

    grade = st.sidebar.selectbox(
        "Grade",
        grades,
        index=grades.index(current_grade)
    )
    age = st.sidebar.number_input(
        "Age",
        min_value=5,
        max_value=25,
        value=int(st.session_state.get("age", 10))
    )
    favorite_subject = st.sidebar.text_input("Favorite Subject", value=st.session_state.get("favorite_subject") or "")
    weak_subject = st.sidebar.text_input("Weak Subject", value=st.session_state.get("weak_subject") or "")
    learning_style = st.sidebar.selectbox("Learning Style", ["Visual", "Practical", "Reading/Writing", "Interactive", "Story-based"])
    language = st.sidebar.selectbox("Preferred Language", ["English", "Kiswahili", "Sheng"])

    # Composite state verification logic to load specific student thread context safely
    if name:
        if (st.session_state.get("last_checked_name") != name or 
            st.session_state.get("last_checked_grade") != grade or 
            st.session_state.get("last_checked_age") != int(age)):
            
            st.session_state.messages = get_chat_history(name, grade, int(age))
            st.session_state.last_checked_name = name
            st.session_state.last_checked_grade = grade
            st.session_state.last_checked_age = int(age)
        st.session_state.student_name = name

    # CBC CURRICULUM INTEGRATION SELECTORS
    st.sidebar.markdown("---")
    st.sidebar.subheader(" Curriculum Context")

    # 1. Safely pull Grade dictionary
    grade_dict = CBC.get(grade, {})
    if not isinstance(grade_dict, dict):
        grade_dict = {}

    subjects = list(grade_dict.keys()) or ["General Studies"]
    # Added unique key
    subject = st.sidebar.selectbox("Subject", subjects, key="sidebar_subject_select")

    # 2. Safely pull Subject dictionary
    subject_dict = grade_dict.get(subject, {})
    if not isinstance(subject_dict, dict):
        subject_dict = {}

    topics = list(subject_dict.keys()) or ["General Topic"]
    # Added unique key
    topic = st.sidebar.selectbox("Topic", topics, key="sidebar_topic_select")

    # 3. Handle structure split gracefully (3-level vs 4-level deep data layouts)
    inner_data = subject_dict.get(topic, {})

    if isinstance(inner_data, dict):
        sub_topics = list(inner_data.keys()) or ["General Sub-Topic"]
        # Added unique key for dictionary branch
        sub_topic = st.sidebar.selectbox("Sub-topic", sub_topics, key="sidebar_subtopic_dict_select")
        outcomes = inner_data.get(sub_topic, []) or ["General Learning Outcome"]
    else:
        # Added unique key for list branch
        sub_topic = st.sidebar.selectbox("Sub-topic", ["General Sub-Topic"], key="sidebar_subtopic_list_select")
        outcomes = inner_data if isinstance(inner_data, (list, tuple)) else ["General Learning Outcome"]

    # 4. Enforce strict unique key for outcomes selectbox
    raw_outcome = st.sidebar.selectbox("Learning Outcome", outcomes, key="sidebar_outcome_select")
    learning_outcome = str(raw_outcome) if raw_outcome else "General Learning Outcome"

    # Assemble Complete Multi-Dimensional Student Object Map
    student = {
        "name": name if name else "Student",
        "grade": grade,
        "age": int(age),
        "favorite_subject": favorite_subject,
        "weak_subject": weak_subject,
        "learning_style": learning_style,
        "language": language,
        "subject": subject,
        "topic": topic,
        "sub_topic": sub_topic,
        "learning_outcome": learning_outcome
    }

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
    # NAVIGATION HUB
        # =====================================================================
    # --- NAVIGATION HUB WITH DYNAMIC GENERATOR TOGGLE ---
    # =====================================================================
    st.sidebar.markdown("### Navigation Hub")
    
    # 1. Voice Tutor Mode Button (Stays at the top of the hub)
    if st.sidebar.button("🎙️ Voice Tutor Mode", use_container_width=True, key="sb_nav_voice"):
        st.session_state.current_page = "Voice Tutor"
        st.rerun()
        
    # ---------------------------------------------------------------------
    # DYNAMIC BUTTON: Switches text and behavior based on the active page
    # ---------------------------------------------------------------------
    current_active_page = st.session_state.get("current_page", "Main Chat")
    
    if current_active_page == "Generators Hub":
        # If the user is inside the Hub, show the return path button
        if st.sidebar.button("💬 Back to Ask Mwalimu", use_container_width=True, key="sb_dynamic_back_chat"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
    else:
        # If the user is anywhere else, show the entrance button to the Hub
        if st.sidebar.button("⚡ Go to Quizzes, Flashcards and Lessons Generator", use_container_width=True, key="sb_dynamic_go_hub"):
            st.session_state.current_page = "Generators Hub"
            st.rerun()
    # ---------------------------------------------------------------------

    # 3. Clear Chat Button (Moved cleanly to the bottom of the navigation block)
    if st.sidebar.button("🗑️ Clear Chat", use_container_width=True, key="sb_nav_clear_chat"):
        # Ensure your student_name, grade, and age fallbacks exist inside local scopes
        clear_student_chat_history(
            student_name=st.session_state.get("student_name", "Student"),
            grade=st.session_state.get("grade", "Grade 6"),
            age=int(st.session_state.get("age", 12))
        )
        st.session_state.messages = []
        st.toast("Chat history cleared cleanly!", icon="🗑️")
        st.rerun()


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
                
                # MOVED INSIDE SIDEBAR: Verification button for free users who just paid
                if st.sidebar.button("💳 I've Paid, Check Status", use_container_width=True):
                    # ----------------------------------------------------------------
                    # TEMPORARY MOCK PAYMENT TRIGGER (REMOVE BEFORE PRODUCTION)
                    # ----------------------------------------------------------------
                    from datetime import datetime, timedelta
                    
                    mock_expiry = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
                    mock_subscription = {
                        "tier": "Premium",  # Change this to "Mwalimu AI Plus" to test that tier too
                        "expiry_date": mock_expiry,
                        "payment_status": "Completed",
                        "reference_id": "MOCK_PAYMENT_12345"
                    }
                    
                    # Directly update your Firestore user document layout
                    from services.database import db
                    uid = st.session_state.get("uid") or st.session_state.user_email
                    db.collection('users').document(str(uid)).update({
                        "subscription": mock_subscription
                    })
                    st.sidebar.success("🔧 Mock Payment Simulated!")
                    # ----------------------------------------------------------------

                    # Refresh data from database to check if everything updates live
                    user_data = get_student_data(st.session_state.user_email)
                    subscription = user_data.get('subscription', {}) if user_data else {}
                    updated_tier = subscription.get('tier', 'Free')
                    
                    if str(updated_tier).strip().lower() != "free":
                       st.sidebar.success(f"Upgrade successful! You are now {updated_tier}")
                       st.rerun()
                    else:
                       st.sidebar.warning("Payment not confirmed yet. Please wait a moment.")


        # 2. Trigger the modal based on state
        if st.session_state.get("show_upgrade_modal"):
            show_upgrade_modal()

        # 3. Log Out Button (Kept at the bottom of the sidebar)
        st.sidebar.markdown("---") # Visual separator
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.user_authenticated = False
            st.session_state.user_profile = None
            st.session_state.messages = []
            st.session_state.show_upgrade_modal = False
            st.rerun()

    # Call the function to render the complete sidebar layout
    render_workspace_sidebar()


    #--- SIDEBAR PROGRESS DASHBOARD GENERATION
    st.sidebar.markdown("---")
    st.sidebar.subheader(" Progress Dashboard")
    if name:
        stats = get_student_stats(name, grade, int(age))
        st.sidebar.metric(label="Quizzes Taken", value=stats["quizzes"])
        st.sidebar.metric("Average Score", f"{stats.get('average_score', 0)}%")
        
        analysis = get_student_learning_analysis(name, grade, int(age))
        st.sidebar.markdown(f"**Learning Status:** `{analysis.get('current_level', 'Medium')}`")
        
        if analysis.get('weak_topics'):
            st.sidebar.markdown("**Needs Improvement:**")
            for t in analysis['weak_topics']:
                st.sidebar.caption(f"⚠️ {t}")
                
        if analysis.get('strong_topics'):
            st.sidebar.markdown("**Mastered Areas:**")
            for t in analysis['strong_topics']:
                st.sidebar.caption(f"✅ {t}")
                
        history_scores = get_student_quiz_history(name, grade, int(age))
        if len(history_scores) > 0:
            st.sidebar.markdown("**Performance Trend**")
            st.sidebar.line_chart(history_scores)
    else:
        st.sidebar.caption("Fill in your name to start tracking parameters.")

    #======
                    # =====================================================================
    # --- INTEGRATED SIDEBAR USAGE BALANCES ---
    # =====================================================================
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔋 Daily Generation Limits")

    # 1. Pipeline profile & data lookups cleanly inside sidebar scope
    sidebar_profile_raw = get_student_data(st.session_state.user_email)
    sidebar_profile = sidebar_profile_raw if sidebar_profile_raw is not None else {}
    sb_sub_tree = sidebar_profile.get('subscription', {}) if isinstance(sidebar_profile.get('subscription'), dict) else {}
    sb_current_plan = str(sb_sub_tree.get('tier', 'Free')).strip()

    # 2. Extract specific limit structures mapping from tier_guard module configs
    from services.tier_guard import TIER_LIMITS
    sb_limits_key = "Free"
    if "plus" in sb_current_plan.lower():
        sb_limits_key = "Mwalimu AI Plus"
    elif "premium" in sb_current_plan.lower():
        sb_limits_key = "Premium"

    sb_user_limits = TIER_LIMITS.get(sb_limits_key, TIER_LIMITS["Free"])

    # 3. Read usage tracking entries using verified tracking id string keys
    sb_uid = str(st.session_state.get("uid") or st.session_state.user_email)
    
    # Fetch Limits Configuration Values
    sb_q_limit = sb_user_limits.get("quizzes", 1)
    sb_fc_limit = sb_user_limits.get("flashcards", 1)
    sb_lesson_limit = sb_user_limits.get("lessons", 1)
    sb_ask_limit = sb_user_limits.get("questions", 1)
    sb_plan_limit = sb_user_limits.get("has_study_plan", 1)

    # Fetch Current Daily Usage Stats Metrics
    sb_q_used = MwalimuDBService.get_daily_usage(sb_uid, "quizzes")
    sb_fc_used = MwalimuDBService.get_daily_usage(sb_uid, "flashcards")
    sb_lesson_used = MwalimuDBService.get_daily_usage(sb_uid, "lessons")
    sb_ask_used = MwalimuDBService.get_daily_usage(sb_uid, "questions")
    sb_plan_used = MwalimuDBService.get_daily_usage(sb_uid, "has_study_plan")

    # 4. Formulate clean conditional balance labels strings text
    def format_sb_balance(used, max_limit):
        if max_limit == float('inf'):
            return f"{used} / ∞ (Unlimited)"
        remaining = max(0, max_limit - used)
        return f"{remaining} left (of {max_limit})"

    # 5. Render compact, text-based metric slots inside the dark sidebar
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

    st.sidebar.markdown(f"📖 **Lessons:** `{format_sb_balance(sb_lesson_used, sb_lesson_limit)}`")
    if sb_lesson_limit != float('inf') and sb_lesson_used >= sb_lesson_limit:
        st.sidebar.caption("⚠️ Lesson limit reached for today.")



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
                    local_metrics = get_student_stats(name, grade, age_int)
                    st.session_state.study_plan = generate_study_plan(student_profile, local_metrics)
                    
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

        # -----------------------------
        # Display previous chat messages
        # -----------------------------
        for msg in st.session_state.messages:
            role = "user" if msg["role"] in ["student", "user"] else "assistant"

            with st.chat_message(role):
                st.markdown(msg["content"])

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
        user_question = st.chat_input("Ask Mwalimu anything...")

        if user_question:
            # 1. Safely retrieve user data
            student_profile = get_student_data(st.session_state.user_email)
            subscription = student_profile.get("subscription", {}) if student_profile else {}
            tier = subscription.get("tier", "Free")
            uid = st.session_state.get("uid") or st.session_state.user_email

            if not name:
                st.warning("Please create Student Profile in the sidebar first!")
            
            # 2. Gatekeeper Check
            elif not verify_tier_allowance(uid, tier, "questions"):
                # Flag the limit state to render the warning button block safely on next loop pass
                st.session_state.chat_limit_reached = True
                st.rerun()
                    
            else:
                # Clear any lingering warning states since execution is valid
                st.session_state.pop("chat_limit_reached", None)

                # 3. Process Request
                st.session_state.messages.append({"role": "student", "content": user_question})
                save_chat_message(name, grade, int(age), "student", user_question)
                
                with st.spinner("Mwalimu is thinking..."):
                    response = ask_mwalimu(user_question, student=student, messages=st.session_state.messages[:-1])
                    
                # 4. Critical: Increment usage AFTER successful response
                MwalimuDBService.increment_usage(uid, "questions")
                
                # Save and Rerun
                st.session_state.messages.append({"role": "assistant", "content": response})
                save_chat_message(name, grade, int(age), "assistant", response or "")
                st.rerun()

   # PAGE VIEW MODE 2: VOICE TUTOR DASHBOARD MODE
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
                    from openai import OpenAI
                    client_gate = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
                    render_voice_tutor_page(client_gate)
                else:
                    st.error("OpenRouter Gateway API configurations are currently offline.")
            else:
                # 3. Handle the blocked state
                st.warning("🎙️ **Voice Tutor Mode is a Premium Feature.**")
                st.info("Upgrade to Premium to unlock interactive audio learning and more!")
                if st.button("🚀 Upgrade to Premium", key="voice_upgrade"):
                    show_upgrade_modal()

    #======
    elif st.session_state.current_page == "Edit Profile":
        st.markdown("---")
        if st.button("⬅ Back to Main Chat Dashboard", use_container_width=True):
            st.session_state.current_page = "Main Chat"
            st.rerun()
            
        st.subheader("⚙ Edit Student Profile")
        st.write("Keep your academic milestones up to date. Changing your baseline grade helps Mwalimu AI adjust the difficulty of quizzes and voice tasks automatically.")
        
        # 1. Fetch active data parameters cleanly
        current_uid = st.session_state.get("uid") or st.session_state.get("user_email")
        user_doc_ref = db.collection("users").document(str(current_uid))
        active_profile = user_doc_ref.get().to_dict() or {}
        
        if active_profile:
            with st.container(border=True):
                # 2. Keep Name and Email locked (Read-Only Layout)
                st.text_input("Student Name", value=active_profile.get("name", st.session_state.get("student_name", "Student")), disabled=True)
                st.text_input("Registered Email Address", value=active_profile.get("email", st.session_state.get("user_email", "")), disabled=True)
                
                # 3. Allow only Grade and Age to change
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
                confirm_reset = st.checkbox("I understand and authorize Mwalimu AI to re-align my progress tracking records to this new grade.")
                
                # 6. Execution validation button pipeline
                if st.button("Save Profile Settings", use_container_width=True, type="primary"):
                    if not confirm_reset:
                        st.error("Please acknowledge the progress re-alignment warning checkbox above before saving modifications.")
                    else:
                        with st.spinner("Re-aligning your academic workspace profile..."):
                            # A. Update document values inside Firestore collection mapping
                            user_doc_ref.update({
                                "grade": new_grade,
                                "age": int(new_age)
                            })
                            
                            # B. Clear performance collection histories matched to this specific user ID
                            # Add whatever tracking collection schemas your system creates over time
                            collections_to_wipe = ["quiz_history", "learning_analysis", "quiz_results", "student_progress"]
                            for target_col in collections_to_wipe:
                                try:
                                    stale_docs = db.collection(target_col).where("uid", "==", str(current_uid)).stream()
                                    for doc_item in stale_docs:
                                        db.collection(target_col).document(doc_item.id).delete()
                                except Exception:
                                    pass # Prevent interruptions if an optional analytics collection doesn't exist yet
                            
                            # C. Synchronize state keys locally to immediate runtime context
                            st.session_state.grade = new_grade
                            st.session_state.age = int(new_age)
                            if st.session_state.user_profile:
                                st.session_state.user_profile["grade"] = new_grade
                                st.session_state.user_profile["age"] = int(new_age)
                                
                            st.toast("🎉 Profile settings synchronized successfully!")
                            st.session_state.current_page = "Main Chat"
                            st.rerun()
        else:
            st.error("Unable to load active profile registry parameters from database data stores.")

    # PAGE VIEW MODE 3: GENERATORS WORKSPACE HUB
    elif st.session_state.current_page == "Generators Hub":
        st.markdown("---")
        student_profile = get_student_data(st.session_state.user_email)
        if st.button("Go back to Main Chat Dashboard", use_container_width=True, key="back_from_generators"):
            st.session_state.current_page = "Main Chat"
            st.rerun()

        st.markdown("---")

        #=== GENERATOR TABS======
       
        tab1, tab2, tab3 = st.tabs(["Quiz Generator Engine", "AI Flashcards Maker", "AI Lessons Generator"])
        with tab1:
            st.subheader("Quiz Generator")
            
            # 1. Guard topic string assignment safely
            raw_quiz_input = st.text_input(
                "Quiz Topic", 
                placeholder="Defaults to current dynamic Sub topic selection", 
                value=sub_topic if 'sub_topic' in locals() else "", 
                key="workspace_quiz_topic"
            )
            quiz_topic: str = raw_quiz_input.strip() if raw_quiz_input else ""
            
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
            
            # Normalize user_tier to match your tier guard system
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
                        
                        # Replace undefined variable references safely with dictionary values
                        quiz_result = generate_quiz(quiz_topic, student_profile, target_diff)
                        
                        if quiz_result:
                            st.session_state.quiz = quiz_result
                            st.session_state.quiz_submitted = False
                            st.session_state.quiz_score = 0
                            st.session_state.quiz_raw_score = 0
                            
                            MwalimuDBService.increment_usage(uid, "quizzes")
                            
                            if not verify_tier_allowance(uid, user_tier, "quizzes"):
                                st.session_state.quiz_limit_reached = True
                            
                            save_activity(
                                student_name=name,
                                student_grade=grade,
                                student_age=age_int,
                                activity_type="quiz_generation",
                                topic=quiz_topic,
                                score=0,
                                subject=subject if 'subject' in locals() and subject else "General",
                                topics=topic if 'topic' in locals() and topic else "General",
                                sub_topic=sub_topic if 'sub_topic' in locals() and sub_topic else "General",
                                learning_outcome=learning_outcome if 'learning_outcome' in locals() and learning_outcome else "General"
                            )
                            st.rerun()
                            
            # ----------------------------------------------------
            # Render Active Quiz Layout (Stays open across user interactions)
            # ----------------------------------------------------
            if st.session_state.quiz:
                st.markdown("### Generated Quiz")
                for i, question in enumerate(st.session_state.quiz):
                    st.markdown(f"#### Question {i+1}")
                    st.radio(
                        question["question"],
                        question["options"],
                        index=None,
                        key=f"q_{i}",
                        disabled=st.session_state.get("quiz_submitted", False)
                    )
                    
                # Submit handling block
                if not st.session_state.get("quiz_submitted", False):
                    if st.button("Submit Quiz", use_container_width=True):
                        current_answers = [st.session_state.get(f"q_{i}") for i in range(len(st.session_state.quiz))]
                        if None in current_answers:
                            st.warning("Please answer all questions before submitting.")
                        else:
                            score = 0
                            for i, q in enumerate(st.session_state.quiz):
                                if current_answers[i] == q["answer"]:
                                    score += 1
                            st.session_state.quiz_raw_score = score
                            st.session_state.quiz_score = round((score / len(st.session_state.quiz)) * 100)
                            st.session_state.quiz_submitted = True
                            
                            save_activity(
                                student_name=name, student_grade=grade, student_age=age_int,
                                activity_type="quiz_score", topic=quiz_topic,
                                score=st.session_state.quiz_score,
                                subject=subject if 'subject' in locals() and subject else "General", 
                                topics=topic if 'topic' in locals() and topic else "General", 
                                sub_topic=sub_topic if 'sub_topic' in locals() and sub_topic else "General",
                                learning_outcome=learning_outcome if 'learning_outcome' in locals() and learning_outcome else "General"
                            )
                            st.rerun()

                # ----------------------------------------------------                               
                # Post-Submission Review Display
                # ----------------------------------------------------
                if st.session_state.get("quiz_submitted", False):
                    raw_score = st.session_state.get("quiz_raw_score", 0)
                    total_questions = len(st.session_state.quiz) if st.session_state.quiz else 0
                    percentage = st.session_state.get("quiz_score", 0)
                    
                    st.success(f"📊 You scored {raw_score}/{total_questions} ({percentage}%)")
                    
                    st.markdown("### 🔍 Answer Review")
                    for i, q in enumerate(st.session_state.quiz):
                        student_answer = st.session_state.get(f"q_{i}")
                        correct_answer = q.get("answer")
                        
                        st.markdown(f"**Question {i+1}**")
                        st.write(q.get("question"))
                        st.write(f"👉 **Your Answer:** {student_answer}")
                        
                        if student_answer == correct_answer:
                            st.success(f"✅ Correct Answer: {correct_answer}")
                        else:
                            st.error(f"❌ Correct Answer: {correct_answer}")
                            
                    # Clear layout to reset state controls cleanly
                    if st.button("Clear Quiz Results", use_container_width=True):
                        st.session_state.quiz = None
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_raw_score = 0
                        
                        # Check remaining limits using the validated tracking parameters
                        if not verify_tier_allowance(uid, user_tier, "quizzes"):
                            st.session_state.quiz_limit_reached = True
                        st.rerun()



        #=====Flash Card ====
                        
        with tab2:
            st.subheader("AI Flashcards Maker")
            
            # Ensure input string extraction can never evaluate as NoneType
            raw_fc_input = st.text_input("Enter a topic for your flashcards:", value=sub_topic if 'sub_topic' in locals() else "", key="fc_topic")
            flashcard_topic: str = raw_fc_input.strip() if raw_fc_input else ""
            
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
            if "flashcards" not in st.session_state or not isinstance(st.session_state.flashcards, list):
                st.session_state.flashcards = []
                
            has_active_flashcards = len(st.session_state.flashcards) > 0

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
                show_upgrade_modal()

            # ----------------------------------------------------
            # Flashcards Generation Action Trigger
            # ----------------------------------------------------
            if st.button("Generate Flashcards", use_container_width=True):
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
                        # Replace undefined 'student' reference with clean dictionary payload
                        fc_result = generate_flashcards(flashcard_topic, student_profile)
                        
                        # Fallback parsing support if model output is a raw JSON string instead of an unrolled list
                        if isinstance(fc_result, str):
                            import json
                            try:
                                fc_result = json.loads(fc_result)
                            except Exception:
                                # Convert raw text strings directly to a valid card format to prevent system crashes
                                fc_result = [{"question": "Topic Summary", "answer": fc_result}]

                        st.session_state.flashcards = fc_result if isinstance(fc_result, list) else []
                        
                        MwalimuDBService.increment_usage(uid, "flashcards")
                        
                        if not verify_tier_allowance(uid, user_tier, "flashcards"):
                            st.session_state.flashcards_limit_reached = True
                        st.rerun()

            # ----------------------------------------------------
            # SAFE DISPLAY LAYER: Prevents 'str object has no attribute get'
            # ----------------------------------------------------
            if st.session_state.flashcards:
                st.info("💡 Click 'Show Answer' to test your active recall memory knowledge!")
                
                for idx, card in enumerate(st.session_state.flashcards):
                    # Direct data mutation guard check: ensure item is a dictionary object
                    if isinstance(card, dict):
                        q_text = card.get("question", "No question text provided")
                        a_text = card.get("answer", "No answer text provided")
                    else:
                        # Fallback if list contains raw string objects
                        q_text = f"Card details text format variant {idx + 1}"
                        a_text = str(card)

                    st.markdown(f"### Flashcard {idx + 1}")
                    st.write(f"**❓ Question:** {q_text}")
                    
                    with st.expander("👁️ Show Answer"):
                        st.success(f"**💡 Answer:** {a_text}")
                
                if st.button("Clear Flashcards", use_container_width=True):
                    st.session_state.flashcards = []
                    if not verify_tier_allowance(uid, user_tier, "flashcards"):
                        st.session_state.flashcards_limit_reached = True
                    st.rerun()


                    
        with tab3:
            st.subheader("AI Lessons Generator")
            
            # Protect lesson text input string binding variables
            raw_lesson_input = st.text_input("Enter the topic you want to learn today:", value=learning_outcome, key="lesson_topic_input")
            lesson_topic: str = raw_lesson_input.strip() if raw_lesson_input else ""
            
            # Fetch student tier profile data upfront
            student_profile = get_student_data(st.session_state.user_email)
            subscription = student_profile.get("subscription", {}) if student_profile else {}
            user_tier = subscription.get("tier", "Free")
            uid = st.session_state.get("uid") or st.session_state.user_email
            
            # Check if there is active lesson content currently displayed on screen
            has_active_lesson = "lesson_content" in st.session_state and st.session_state.lesson_content is not None

            # ----------------------------------------------------
            # State-Driven Upgrade Gatekeeper Banner
            # ----------------------------------------------------
            # Only show the limit banner if they reached the limit and are NOT currently reading a lesson
            if st.session_state.get("lessons_limit_reached") and not has_active_lesson:
                st.error("⚠️ Lessons Limit Reached, Wait for 24hrs or Upgrade to Premium to continue!")
                
                if st.button("🚀 Upgrade to Premium", key="lesson_upgrade_unique_btn"):
                    # 1. Clear the banner state flag immediately 
                    st.session_state.pop("lessons_limit_reached", None)
                    
                    # 2. Stage a temporary trigger instead of a permanent True state
                    st.session_state.trigger_lesson_upgrade_modal = True
                    st.rerun()

            # ----------------------------------------------------
            # Safe Modal Activation Layer (Prevents Continuous Loops)
            # ----------------------------------------------------
            if st.session_state.get("trigger_lesson_upgrade_modal"):
                # Instantly remove the flag so it only runs EXACTLY once
                st.session_state.pop("trigger_lesson_upgrade_modal", None)
                show_upgrade_modal()

            # ----------------------------------------------------
            # Lessons Generation Action Trigger
            # ----------------------------------------------------
            if st.button("Generate Lesson", use_container_width=True):
                if not lesson_topic:
                    st.warning("Please enter a valid lesson topic first!")
                elif not name:
                    st.warning("Please create Student Profile in the sidebar first!")
                
                # Guard tier allowance at the moment of clicking (matches the specific 'lessons' rule context)
                elif not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                    # Flag the limit state to render the warning button block safely on next loop pass
                    st.session_state.lessons_limit_reached = True
                    st.rerun()
                else:
                    # Clear any lingering warning states since execution is valid
                    st.session_state.pop("lessons_limit_reached", None)

                    with st.spinner("Mwalimu AI is preparing your personalized lesson..."):
                        try:
                            st.session_state.lesson_content = generate_lesson(lesson_topic, student)
                            
                            # Deduct the remaining balance token instantly after generation
                            MwalimuDBService.increment_usage(st.session_state.user_email, "lessons")
                            
                            # Double-check if that last click used up the allowance balance
                            if not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                                st.session_state.lessons_limit_reached = True
                                
                            save_activity(
                                student_name=name, student_grade=grade, student_age=int(age),
                                activity_type="lesson", topic=lesson_topic, score=0,
                                subject=subject if subject else "General", 
                                topics=topic if topic else "General", 
                                sub_topic=sub_topic if sub_topic else "General",
                                learning_outcome=learning_outcome if learning_outcome else "General"
                            )
                        except Exception as e:
                            st.error(f"Failed to generate lesson: {str(e)}")
                        st.rerun()
                        
            # ----------------------------------------------------
            # Render Active Lesson Layout
            # ----------------------------------------------------
            if "lesson_content" in st.session_state and st.session_state.lesson_content:
                st.markdown("---")
                st.info("Tip: Read through the breakdown below. Mwalimu customized this explanation precisely for your style!")
                
                raw_lesson = st.session_state.lesson_content
                if raw_lesson and isinstance(raw_lesson, str):
                    safe_lesson: str = raw_lesson
                    
                    if safe_lesson.startswith("```markdown"):
                        safe_lesson = safe_lesson.replace("```markdown", "", 1).rstrip("```")
                    elif safe_lesson.startswith("```"):
                        safe_lesson = safe_lesson.strip("```")
                    st.markdown(safe_lesson)
                else:
                    st.write(raw_lesson)
                    
                if st.button("Clear Lesson Content", use_container_width=True):
                    st.session_state.lesson_content = None
                    
                    # Check limits again. If they were out of limits, the banner will now reappear cleanly
                    if not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                        st.session_state.lessons_limit_reached = True
                    st.rerun()



#===========================
#=== LANDING PAGE ========
#============================

else:
    try:
        with open("assets/logo211.png", "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode()
    except Exception:
        sidebar_bg_style = ""
    
        # 1. Initialize state
    if "show_auth" not in st.session_state:
        st.session_state.show_auth = False

    # 2. Header Layout
    left, middle, right = st.columns([7, 2, 1])
    with left:
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

    with right:
        # Toggle button logic
        if st.session_state.show_auth:
            # Button when in Auth view
            if st.button("Home"):
                st.session_state.show_auth = False
                st.rerun()
        else:
            # Button when on Landing page
            if st.button("Sign Up for Free"):
                st.session_state.show_auth = True
                st.rerun()

    # 3. View Switcher
    if st.session_state.show_auth:
        st.markdown("""
            <style>

            /* Limit page width */
            [data-testid="stMainBlockContainer"]{
                max-width:960px;
                margin:auto;
                padding-top:3rem;
                padding-bottom:5rem;
            }

            /* Registration card */
            div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stForm"]) {
                max-width:900px;
                margin:auto;
            }

            </style>
            """, unsafe_allow_html=True)
        # --- AUTH PORTAL VIEW ---
        st.markdown("## Join Mwalimu AI")
        render_auth_portal() # Your existing function
    else:
        
        # 2. POLISHED CSS INJECTION
        def inject_polished_css():
            st.markdown("""
            <style>
            /* Dark Mode Theme */
            [data-testid="stAppViewContainer"] { background-color: #020617; }
            
            /* Hero Section */
            .hero-container { padding: 4rem 2rem; text-align: center; }
            .hero-title { font-size: 3.5rem; font-weight: 800; color: #f8fafc; margin-bottom: 1rem; }
            
            /* Feature Card System */
            .card {
                background: #0f172a;
                padding: 30px;
                border-radius: 20px;
                border: 1px solid #1e293b;
                transition: transform 0.2s;
            }
            .card:hover { border-color: #3b82f6; }
            
            /* Metric Styling */
            .metric-box { background: #1e293b; padding: 20px; border-radius: 12px; text-align: center; }
            
            /* Buttons */
            .stButton > button { border-radius: 8px; width: 100%; border: none; background: #3b82f6; color: white; }
            /* ADD THE MEDIA QUERY HERE, AT THE BOTTOM OF THE STYLE BLOCK */
            @media (max-width: 600px) {
                .hero-title { font-size: 2rem !important; }
                .card { padding: 15px; }
            }
            </style>
            """, unsafe_allow_html=True)

        # 3. APP LOGIC
        inject_polished_css()

        # Hero Section

        st.markdown(
            """
            <h2 style="text-align:center; margin:0; line-height:1.2;">
                <span style="font-family:Georgia, serif; color:white;">
                    Your AI Tutor.
                </span>
                <span style="font-family:Arial, sans-serif; color:white;">
                    Your Academic
                </span>
                <span style="font-family:Arial, sans-serif; color:#3b82f6;">
                    Advantage
                </span>
            </h2>

            <p style="text-align:center; color:#94a3b8; margin-top:8px;">
                Powerful tools designed to help every learner reach their full potential.
            </p>
            """,
            unsafe_allow_html=True
        )
                

        # Feature Grid (Card Layout)
        st.subheader("Everything You Need to Excel")
        grid_cols = st.columns(3)
        features = [
            ("📚 CBC Coverage", "Comprehensive content for Grades 1–12."),
            ("🎯 Personalized Study Plans", "AI-driven goals for every student."),
            ("🎙️ AI Voice Tutor", "Interactive learning in Swahili & English.")
        ]
        for i, (title, body) in enumerate(features):
            with grid_cols[i]:
                st.markdown(f"<div class='card'><h3>{title}</h3><p style='color: #94a3b8;'>{body}</p></div>", unsafe_allow_html=True)

        # Auth Portal (Tabbed)
        st.markdown("<br><br>", unsafe_allow_html=True)
        grid_cols = st.columns(4)
        features = [
            ("📊 Performance tracking", "Monitor your mastery and quiz performance by topic."),
            ("📝 Quiz Generator", "Instant practice tests on any topic."),
            ("🤖 AI Lessons Generator", "Custom lessons mapped to every topic."),
            ("🧠 Flashcards Generator", "Effective memory tools for fast revision.")
        ]
        for i, (title, body) in enumerate(features):
            with grid_cols[i]:
                st.markdown(f"<div class='card'><h3>{title}</h3><p style='color: #94a3b8;'>{body}</p></div>", unsafe_allow_html=True)

        # Auth Portal (Tabbed)
        st.markdown("<br><br>", unsafe_allow_html=True)

        # Metrics Grid
        cols = st.columns(4)
        metrics = [("KICD competency-based Curriculum topics", "4,000+"), ("Learning outcomes", "20,000+"), ("KICD competency-based/CBC Aligned", "100%"), ("Rating", "4.8/5")]
        for i, (label, val) in enumerate(metrics):
            with cols[i]:
                st.markdown(f"<div class='metric-box'><h3>{val}</h3><p>{label}</p></div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)


        # --- 1. DEFINE THE UNIFIED FUNCTION ---


        # --- 1. DEFINE THE UNIFIED FUNCTION WITH EMBEDDED ENGINE HOOKS ---
        # --- 1. DEFINE THE UNIFIED FUNCTION WITH CLEAN ST.HTML RENDERING ---
        def render_tier_card_html(title, description, card_features, color_bg, is_premium=False, button_key=""):
            """
            Renders a premium SaaS layout card using Streamlit's native st.html wrapper.
            Guarantees 100% type safety and completely clears Pylance errors.
            """
            border_accent = "#fbbf24" if is_premium else "#3b82f6"
            badge_html = "<span style='background: #fbbf24; color: #020617; font-size: 0.7rem; font-weight: bold; padding: 3px 8px; border-radius: 20px; float: right; letter-spacing: 0.05em;'>POPULAR</span>" if is_premium else ""
            
            # Compile features list into plain HTML strings cleanly
            features_html = ""
            for item in card_features:
                features_html += f"""
                <li style="margin-bottom: 10px; display: flex; align-items: flex-start; font-size: 0.88rem; line-height: 1.3;">
                    <span style="color: {border_accent}; font-weight: bold; margin-right: 8px; flex-shrink: 0;">✓</span>
                    <div>{str(item)}</div>
                </li>
                """

            # Pure, clean layout injected directly into the active viewport container
            card_html = f"""
            <div style="
                background-color: {color_bg}; 
                padding: 24px 20px; 
                border-radius: 16px; 
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-top: 5px solid {border_accent}; 
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
                min-height: 380px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            ">
                <div>
                    {badge_html}
                    <h3 style="margin: 0 0 6px 0; font-size: 1.35rem; font-weight: 700;">{title}</h3>
                    <div style="color: #94a3b8; font-size: 0.88rem; margin: 0 0 14px 0; line-height: 1.4; min-height: 36px;">{description}</div>
                </div>
                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.08); margin: 0 0 16px 0;">
                <ul style="list-style: none; padding: 0; margin: 0; flex-grow: 1;">
                    {features_html}
                </ul>
            </div>
            """
            
            # ----------------------------------------------------
            # FIXED: Replaced components.iframe with native st.html
            # ----------------------------------------------------
            st.html(card_html)
            
            # Render native interactive execution buttons directly in Streamlit space below
            st.markdown("<div style='margin-top: 10px; margin-bottom: 20px;'>", unsafe_allow_html=True)
            if st.button(f"Choose {title}", key=f"btn_action_{button_key}", use_container_width=True):
                st.session_state.show_auth = True
                st.session_state.selected_tier = title
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)



        # --- 2. RENDER THE POLISHED PRICING SECTION ---
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 30px;">
            <h2 style="font-size: 2.3rem; font-weight: 800; color: #f8fafc; margin: 0 0 8px 0;">
                Flexible Tiered Membership Access
            </h2>
            <p style="color: #94a3b8; font-size: 1rem; margin: 0;">
                Pick the right account pace for your regular revisions and curriculum tracking tools.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_free, col_basic, col_prem = st.columns(3, gap="medium")

        with col_free:
            render_tier_card_html(
                title="Mwalimu AI Free", 
                description="Basic daily study toolkit for casual learners.", 
                card_features=[
                    "10 AI Questions / day", 
                    "5 Assessment Quizzes / day",
                    "10 Flashcards generated / day", 
                    "Basic Curriculum Notes", 
                    "No Voice Tutor access", 
                    "No Custom Study Plans"
                ], 
                color_bg="#0f172a",
                is_premium=False,
                button_key="free_tier"
            )

        with col_basic:
            render_tier_card_html(
                title="Mwalimu AI Plus", 
                description="Enhanced toolkit built for dedicated study sessions.", 
                card_features=[
                    "50 AI Questions / day", 
                    "15 Assessment Quizzes / day", 
                    "50 Flashcards generated / day", 
                    "Basic Curriculum Notes", 
                    "Personalized daily Study Plans", 
                    "No Voice Tutor access"
                ], 
                color_bg="#111827",
                is_premium=False,
                button_key="plus_tier"
            )

        with col_prem:
            render_tier_card_html(
                title="Mwalimu Premium", 
                description="Complete school execution dashboard with full feature access.", 
                card_features=[
                    "Unlimited Interactive Prompts", 
                    "Unlimited targeted CBC Quizzes", 
                    "Unlimited Flashcard summaries", 
                    "Full Voice Tutor Mode Enabled", 
                    "Personalized daily Study Plans", 
                    "Advanced Weak-Topic Detection", 
                    "Integrated mobile checkouts"
                ], 
                color_bg="#030712",
                is_premium=True,
                button_key="premium_tier"
            )



        #=====
        # =====================================================================
        # --- LANDING PAGE: SUPPORT CENTER WITH LEGAL NAVIGATION TRIGGER ---
        # =====================================================================
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="font-size: 2rem; font-weight: 700; color: #f8fafc; margin: 0 0 6px 0;">
                Information & Support Center
            </h2>
            <p style="color: #94a3b8; font-size: 0.95rem; margin: 0;">
                Got questions or need to review our platform policies? Explore the tabs below.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Create cohesive navigation tabs for resources
        tab_faq, tab_contact, tab_terms = st.tabs([
            "❓ Frequently Asked Questions", 
            "✉️ Contact Support", 
            "📜 Terms & Conditions"
        ])

        # --- TAB 1: FAQ ACCORDION BLOCK ---
        with tab_faq:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("💳 How do I pay for Mwalimu AI Plus or Premium?"):
                st.write("Payments are securely handled via **M-Pesa STK Push**...")

            with st.expander("⏳ How long does my upgraded tier access last?"):
                st.write("All upgrades provide **30 days of complete access**...")

            with st.expander("🔄 Can I upgrade from Plus to Premium later?"):
                st.write("Yes! You can upgrade your tier level at any time...")

            with st.expander("🎙️ What equipment do I need for the Voice Tutor mode?"):
                st.write("No extra gear is required!...")

        # --- TAB 2: CLEAN SUPPORT FORM ---
        with tab_contact:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form(key="landing_contact_tab_form", clear_on_submit=True):
                col_sender, col_mail = st.columns(2)
                with col_sender:
                    sender_name = st.text_input("Your Name", placeholder="e.g., Jp Cyber")
                with col_mail:
                    sender_email = st.text_input("Your Email Address", placeholder="name@domain.com")
                    
                msg_subject = st.text_input("Subject", placeholder="How can our CBC support desk assist you today?")
                msg_body = st.text_area("Your Message Details", placeholder="Type your question or revision inquiry here...", height=120)
                
                submit_support_btn = st.form_submit_button(label="Submit Secure Message ✨", use_container_width=True)
                if submit_support_btn:
                    # (Your existing form submission processing logic stays here unchanged)
                    pass

        # --- TAB 3: CLEAN ENTRANCE TRIGGER GATE (UPDATED) ---
        with tab_terms:
                    # --- TAB 3: CLEAN ENTRANCE TRIGGER GATE (SIMPLE OVERLAY VERSION) ---
        
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 1. Check if the user has clicked the button to open the full terms
            if st.session_state.get("viewing_full_terms", False):
                st.markdown("## 📜 Standalone Terms & Conditions Center")
                st.caption("📅 Last Updated: July 2026 | CBC Curriculum Engine Sync")
                st.markdown("---")
                
                # Pulls the clean text instantly from your services/legal_text.py file
                from services.legal_text import TERMS_AND_CONDITIONS
                st.write(TERMS_AND_CONDITIONS)
                
                st.markdown("---")
                # Clean button at the bottom to go right back home
                if st.button("⬅️ Accept & Close Document (Return Home)", use_container_width=True, key="close_terms_overlay"):
                    st.session_state.viewing_full_terms = False
                    st.rerun()
            
            # 2. This is what shows by default when they first click the tab
            else:
                st.markdown("### 📜 Platform Terms of Service & End-User License Agreement")
                st.write("""
                To ensure complete transparency regarding your data protection, subscription limits, and M-Pesa non-auto-renewal policies under the Kenyan Data Protection Act, please click the button below to view our comprehensive legal agreement.
                """)
                
                # The button that sets the state to True and opens the writings
                if st.button("⚖️ Read Full Terms of Service", key="trigger_terms_overlay", use_container_width=True):
                    st.session_state.viewing_full_terms = True
                    st.rerun()


        # --- CLEAN LOW-PROFILE FOOTER (REMOVE OLD SEPARATE BLUE BUTTON) ---
        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #64748b; font-size: 0.85rem;'>© 2026 Mwalimu AI App. All Rights Reserved. Mapping Kenyan CBC Excellence.</p>", unsafe_allow_html=True)






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
        {logo_html_tag} Mwalimu AI App Version 2.0 | CBC Curriculum Engine | © 2026 Copyright
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
