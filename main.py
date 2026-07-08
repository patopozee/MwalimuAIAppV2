import base64
import os
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
import requests
from services.auth_service import MwalimuAuthService
from services.payment_service import MpesaPaymentService
from services.tier_guard import verify_tier_allowance
from services.ai import ask_mwalimu, generate_quiz, generate_study_plan, generate_flashcards, generate_lesson
from services.db_service import MwalimuDBService
from services.ui_components import show_upgrade_modal
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

# INITIALIZATION
load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
create_tables()

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="Mwalimu AI App", layout="wide")
# --- HEADER AREA ---
header_col1, header_col2 = st.columns([8, 1])
def render_auth_portal(context="auth"):
    # If a user selected a tier, show them what they are signing up for
    if "selected_tier" in st.session_state:
        st.info(f"You are signing up for: **{st.session_state.selected_tier}**")   
    tab_login, tab_signup, tab_google = st.tabs(["🔑 Login", "✨ Sign Up", "🔵 Google"])
    
    with tab_login:
        with st.container(border=True):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_pass")
            if st.button("Log In to Workspace", use_container_width=True):
                if email.strip() and password.strip():
                    with st.spinner("Verifying credentials..."):
                        auth_res = MwalimuAuthService.login_user(email.strip(), password.strip())
                        if auth_res.get("success"):
                            st.session_state.user_email = email.strip().lower()
                            uid = str(auth_res.get("uid", ""))
                            db_profile = get_student_data(uid) 
                            
                            # Check if profile exists before trying to use it
                            if db_profile and isinstance(db_profile, dict):
                                st.session_state.user_authenticated = True
                                st.session_state.student_name = str(db_profile.get("name", "Unknown"))
                                st.session_state.grade = str(db_profile.get("grade", "Grade 1"))
                                st.session_state.age = int(db_profile.get("age", 10))
                                st.session_state.user_profile = db_profile
                                st.rerun()
                            else:
                                # If the database returns None, handle it gracefully instead of crashing
                                st.error("Profile not found for this user. Please register your profile.")
                        else:
                            st.error(f"Login Failed: Please try again. Error: {auth_res.get('error')}")


        
    with tab_signup:
        with st.container(border=True):
            # --- STEP 1: INITIAL SIGNUP FORM ---
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
                
                if st.button("Register account"):
                    # Validation checks
                    if not reg_name.strip():
                        st.warning("Please enter your name.")
                    elif not reg_email.strip():
                        st.warning("Please enter your email address.")
                    elif not reg_pass.strip() or len(reg_pass) < 6:
                        st.warning("Password must be at least 6 characters.")
                    else:
                        with st.spinner("Creating your Mwalimu AI account..."):
                            # MOVED INSIDE THE ELSE BLOCK
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
                entered_code = st.text_input("Verification Code")
                
                if st.button("Complete Registration"):
                    @st.dialog("Choose Your Premium Plan")
                    def upgrade_modal():
                        st.write("Unlock unlimited access to the full Mwalimu AI toolkit!")
                        
                        # Reuse your existing render_tier_card logic here to show the plans
                        col1, col2 = st.columns(2)
                        with col1:
                            render_tier_card("Mwalimu AI Plus", "...", [...], "#1e593c")
                        with col2:
                            render_tier_card("Mwalimu AI Premium", "...", [...], "#1e3a8a")

                    # In your main app loop
                    if st.session_state.get("show_upgrade_modal"):
                        show_upgrade_modal()
                    res = MwalimuAuthService.finalize_registration(
                        st.session_state.pending_verification, 
                        entered_code
                    )
                    
                    if res.get("success"):
                        st.success("✅ Account verified and created! Go back to Sign In to access your workspace.")
                        del st.session_state.pending_verification # Reset the flow
                    else:
                        st.error(res.get("error"))

        
    with tab_google:
        with st.container(border=True):
            st.write("Fast access via Google:")
            auth_url = (
                "https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={st.secrets['google_oauth']['client_id']}&"
                "redirect_uri=http://localhost:8501/&"
                "response_type=code&"
                "scope=openid%20profile%20email&"
                "prompt=select_account"
            )
            def get_base64_image(image_path):
                if os.path.exists(image_path):
                    with open(image_path, "rb") as f:
                        return base64.b64encode(f.read()).decode()
                return ""
            google_logo_b64 = get_base64_image("assets/google.png")
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={st.secrets['google_oauth']['client_id']}&redirect_uri=http://localhost:8501/&response_type=code&scope=openid%20profile%20email"

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
    if st.button("Forgot Password?"):
        st.session_state.show_reset_form = True

    if st.session_state.get("show_reset_form"):
        reset_email = st.text_input("Enter your registered email")
        if st.button("Send Reset Link"):
            with st.spinner("Sending email..."):
                # Call the function from your service
                result = MwalimuAuthService.send_password_reset_email(reset_email)
                
                if result["success"]:
                    st.success("Check your email for the password reset link!")
                    st.session_state.show_reset_form = False
                else:
                    # Always show a generic message to prevent email enumeration
                    st.error("If the email is registered, you will receive a reset link.")
                    # Optional: Log the actual error in terminal for yourself
                    print(f"Debug Reset Error: {result.get('error')}")

# 🚀 TOP-LEVEL GOOGLE OAUTH INTERCEPTOR
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    try:
        cid = st.secrets["google_oauth"]["client_id"]
        csecret = st.secrets["google_oauth"]["client_secret"]
        
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": auth_code,
            "client_id": cid,
            "client_secret": csecret,
            "redirect_uri": "http://localhost:8501/",
            "grant_type": "authorization_code"
        }
        
        token_response = requests.post(token_url, data=token_data).json()
        
        if "access_token" in token_response:
            user_info = requests.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_response['access_token']}"}
            ).json()
            
            # Sync authentication state fields
            st.session_state.user_authenticated = True
            st.session_state.student_name = user_info.get("name", "Student").strip().title()
            st.session_state.user_profile = {
                "name": st.session_state.student_name,
                "email": user_info.get("email"),
                "grade": "Grade 6", 
                "age": 12,
                "tier": "Free"
            }
            
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"OAuth Exchange Failed: {token_response.get('error_description', 'Unknown Error')}")
    except Exception as e:
        st.error(f"Authentication background sync failed: {str(e)}")

# --- STREAMLIT PAGE CONFIGURATION (MUST BE ABSOLUTE FIRST COMMAND)
st.set_page_config(
    page_title="Mwalimu AI App",
    page_icon="assets/logo112.png",
    layout="wide",
    initial_sidebar_state="expanded"
    
)



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




# ==============================================================================
# ROUTE ROUTER ENGINE
# ==============================================================================

# --- VIEW A: SECURE WORKSPACE DASHBOARD (Logged In State Only) ---
if st.session_state.user_authenticated:
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

    # NAVIGATION HUB
    st.sidebar.subheader(" Navigation Hub")
    if st.sidebar.button("🎙️Voice Tutor Mode", use_container_width=True):
        st.session_state.current_page = "Voice Tutor"
        st.rerun()

    if st.sidebar.button("🗑️Clear Chat"):
        if name:
            try:
                clear_student_chat_history(name, grade, int(age))
            except Exception as e:
                print(f"Error clearing database chat logs: {e}")
            st.session_state.messages = []
            st.session_state.quiz = None
            st.session_state.quiz_submitted = False
            st.session_state.quiz_score = 0
            st.session_state.quiz_raw_score = 0
            st.session_state.flashcards = []
            st.session_state.lesson_content = None
            st.rerun()

    #=== Upgrade Tier === 
    def render_workspace_sidebar():
        if "user_email" in st.session_state:
            user_data = get_student_data(st.session_state.user_email)
            tier = user_data.get('tier', 'Free') if user_data else "Free"

            if str(tier).strip().lower() == "free":
                st.sidebar.info("🚀 Unlock full power with Premium")
                if st.sidebar.button("Upgrade to Premium"):
                    st.session_state.show_upgrade_modal = True
                    st.rerun()

        # Trigger the modal based on state
        if st.session_state.get("show_upgrade_modal"):
            show_upgrade_modal()
            # Reset state after closing the modal so it doesn't loop
            if "close_modal" in st.session_state:
                st.session_state.show_upgrade_modal = False
    render_workspace_sidebar()

        # ===Log Out Button ===
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.user_authenticated = False
        st.session_state.user_profile = None
        st.session_state.messages = []
        st.rerun()

    #--- SIDEBAR PROGRESS DASHBOARD GENERATION
    st.sidebar.markdown("---")
    st.sidebar.subheader(" Progress Dashboard")
    if name:
        stats = get_student_stats(name, grade, int(age))
        st.sidebar.metric("Questions Asked", stats.get("questions", 0))
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
            
        #--- AI STUDY PLAN SECTION
        st.markdown("---")
        st.subheader("AI Personalized Study Plan")
        if st.button("Generate Today's Study Plan", use_container_width=True):
            if not name:
                st.warning("Please create Student Profile in the sidebar first!")
            else:
                with st.spinner("Creating your personalized study plan..."):
                    stats = get_student_stats(name, grade, int(age))
                    st.session_state.study_plan = generate_study_plan(student, stats)
                    st.rerun()
                    
        if st.session_state.study_plan:
            st.info("Tip: Follow the allocated time intervals for maximum focus today!")
            st.markdown(st.session_state.study_plan)
            if st.button("Clear Study Plan"):
                st.session_state.study_plan = None
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
        # Chat Input
        # ----------------------------------------------------
        user_question = st.chat_input("Ask Mwalimu anything...")

        if user_question:
            # 1. Safely retrieve user data
            profile = st.session_state.get("user_profile") or {}
            tier = profile.get("tier", "Free")
            uid = st.session_state.get("user_email")

            if not name:
                st.warning("Please create Student Profile in the sidebar first!")
            
            # 2. Gatekeeper Check
            elif not verify_tier_allowance(uid, tier, "questions"):
                st.error("⚠️ Daily question limit reached. Upgrade to continue!")
                if st.button("Upgrade Now"):
                    st.session_state.show_upgrade_modal = True
                    st.rerun()
                    
            else:
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
            user_data = get_student_data(st.session_state.user_email)
            tier = user_data.get('tier', 'Free') if user_data else "Free"

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
                if st.button("Upgrade to Premium", key="voice_upgrade"):
                    st.session_state.show_upgrade_modal = True
                    st.rerun()

    # PAGE VIEW MODE 3: GENERATORS WORKSPACE HUB
    elif st.session_state.current_page == "Generators Hub":
        st.markdown("---")
        if st.button("Go back to Main Chat Dashboard", use_container_width=True, key="back_from_generators"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
        st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["Quiz Generator Engine", "AI Flashcards Maker", "AI Lessons Generator"])
        with tab1:
            st.subheader("Quiz Generator")
            
            # Guard topic string assignment safely
            raw_quiz_input = st.text_input("Quiz Topic", placeholder="Defaults to current dynamic Sub topic selection", value=sub_topic, key="workspace_quiz_topic")
            quiz_topic: str = raw_quiz_input.strip() if raw_quiz_input else ""
            
            if st.button("Generate Quiz", use_container_width=True):
                if not quiz_topic:
                    st.warning("Please enter a quiz topic.")
                elif not name:
                    st.warning("Please create Student Profile in the sidebar first!")
                else:
                    with st.spinner("Generating quiz..."):
                        target_diff = get_next_difficulty(name, grade, int(age), quiz_topic)
                        st.session_state.quiz = generate_quiz(quiz_topic, student, target_diff)
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_raw_score = 0
                        save_activity(
                            student_name=name,
                            student_grade=grade,
                            student_age=int(age),
                            activity_type="quiz_generation",
                            topic=quiz_topic,
                            score=0,
                            subject=subject if subject else "General",
                            topics=topic if topic else "General",
                            sub_topic=sub_topic if sub_topic else "General",
                            learning_outcome=learning_outcome if learning_outcome else "General"
                        )
                        st.rerun()
                        
            if st.session_state.quiz:
                st.markdown("### Generated Quiz")
                for i, question in enumerate(st.session_state.quiz):
                    st.markdown(f"#### Question {i+1}")
                    st.radio(
                        question["question"],
                        question["options"],
                        index=None,
                        key=f"q_{i}",
                        disabled=st.session_state.quiz_submitted
                    )
                if not st.session_state.quiz_submitted:
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
                                student_name=name, student_grade=grade, student_age=int(age),
                                activity_type="quiz_score", topic=quiz_topic,
                                score=st.session_state.quiz_score,
                                subject=subject if subject else "General", 
                                topics=topic if topic else "General", 
                                sub_topic=sub_topic if sub_topic else "General",
                                learning_outcome=learning_outcome if learning_outcome else "General"
                            )
                            st.rerun()
                            
                if st.session_state.quiz_submitted:
                    raw_score = st.session_state.quiz_raw_score
                    total_questions = len(st.session_state.quiz)
                    percentage = st.session_state.quiz_score
                    st.success(f"You scored {raw_score}/{total_questions} ({percentage}%)")
                    st.markdown("## Answer Review")
                    for i, q in enumerate(st.session_state.quiz):
                        student_answer = st.session_state.get(f"q_{i}")
                        correct_answer = q["answer"]
                        st.markdown(f"### Question {i+1}")
                        st.write(q["question"])
                        st.write(f"**Your Answer:** {student_answer}")
                        if student_answer == correct_answer:
                            st.success(f"Correct Answer: {correct_answer}")
                        else:
                            st.error(f"Correct Answer: {correct_answer}")
                    if st.button("Clear Quiz Results", use_container_width=True):
                        st.session_state.quiz = None
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_raw_score = 0
                        st.rerun()
                        
        with tab2:
            st.subheader("AI Flashcards Maker")
            # Ensure input string extraction can never evaluate as NoneType
            raw_fc_input = st.text_input("Enter a topic for your flashcards:", value=sub_topic, key="fc_topic")
            flashcard_topic: str = raw_fc_input.strip() if raw_fc_input else ""
            
            if st.button("Generate Flashcards", use_container_width=True):
                if not flashcard_topic:
                    st.warning("Please enter a valid topic first!")
                elif not name:
                    st.warning("Please create Student Profile in the sidebar first!")
                else:
                    with st.spinner("Mwalimu AI is writing your flashcards..."):
                        st.session_state.flashcards = generate_flashcards(flashcard_topic, student)
                        st.rerun()
            if st.session_state.flashcards:
                st.markdown("---")
                st.info("Click **'Show Answer'** to test your active recall memory knowledge!")
                for i, card in enumerate(st.session_state.flashcards, start=1):
                    st.markdown(f"### Flashcard {i}")
                    st.write(f"**Question:** {card.get('question', '')}")
                    with st.expander("Show Answer"):
                        st.success(f"**Answer:** {card.get('answer', '')}")
                st.markdown("---")
                if st.button("Clear Flashcards", use_container_width=True):
                    st.session_state.flashcards = []
                    st.rerun()
                    
        with tab3:
            st.subheader("AI Lessons Generator")
            # Protect lesson text input string binding variables
            raw_lesson_input = st.text_input("Enter the topic you want to learn today:", value=learning_outcome, key="lesson_topic_input")
            lesson_topic: str = raw_lesson_input.strip() if raw_lesson_input else ""
            
            if st.button("Generate Lesson", use_container_width=True):
                if not lesson_topic:
                    st.warning("Please enter a valid lesson topic first!")
                elif not name:
                    st.warning("Please create Student Profile in the sidebar first!")
                else:
                    with st.spinner("Mwalimu AI is preparing your personalized lesson..."):
                        try:
                            st.session_state.lesson_content = generate_lesson(lesson_topic, student)
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
                    st.rerun()

#===========================
#=== LANDING PAGE ========
#============================

else:
    st.html(f"""
        <style>
        @media (min-width: 768px) {{
        [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
        [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: 0rem !important; padding-top: 0rem !important; }}
        [data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container {{ padding-top: 1.5rem !important; margin-top: 0rem !important; }}
        }}
        @media (max-width: 767px) {{
        [data-testid="stHeader"], header {{ background-color: transparent !important; height: 3.5rem !important; }}
        [data-testid="stAppViewMainObj"], .stMain, [data-testid="stMain"] {{ margin-top: 0rem !important; padding-top: 0.5rem !important; }}
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
    
        # 1. Initialize state
    if "show_auth" not in st.session_state:
        st.session_state.show_auth = False

    # 2. Header Layout
    left, middle, right = st.columns([7, 2, 1])
    with left:
        col1, col2 = st.columns([1, 8], vertical_alignment="center")
        with col1:
            try:
                st.markdown("""
                <style>
                .logo-container{
                    display:flex;
                    justify-content:center;
                    margin-top:-40px;
                    margin-bottom:10px;
                }
                </style>
                """, unsafe_allow_html=True)

                st.markdown('<div class="logo-container">', unsafe_allow_html=True)
                st.image("assets/logo112.png", width=160)
                st.markdown("</div>", unsafe_allow_html=True)
            except Exception:
                pass
        with col2:
            st.markdown("<h1 style='margin-top: 0 !important; margin-bottom: 0 !important; padding: 0;'>Mwalimu AI App</h1>", unsafe_allow_html=True)
            st.markdown("<h4 style='margin-top: 0px !important; margin-bottom: 0 !important; color: gray; font-weight: normal;'>Shaping Minds, Shifting Futures.</h4>", unsafe_allow_html=True)
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
                padding-bottom:3rem;
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
        def render_tier_card(title, description, features, color_bg, is_premium=False):
            # Add a border-top highlight for premium tiers
            border_style = "4px solid #fbbf24" if is_premium else "4px solid #3b82f6"
            
            st.markdown(f"""
                <div style="background-color: {color_bg}; padding: 25px; border-radius: 12px; border-top: {border_style}; height: 100%; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <h3 style="margin-top:0; color: #ffffff;">{title} {'⭐' if is_premium else ''}</h3>
                    <p style="color: #94a3b8; min-height: 40px;">{description}</p>
                    <hr style="border-color: rgba(255,255,255,0.1);">
                    <ul style="padding-left: 20px; min-height: 250px;">
                        {''.join([f"<li style='margin-bottom: 8px;'>{f}</li>" for f in features])}
                    </ul>
                </div>
            """, unsafe_allow_html=True)
            
            # Button triggers the registration portal with the selected tier pre-loaded
            if st.button(f"Choose {title}", key=f"btn_{title.replace(' ', '_')}"):
                st.session_state.show_auth = True
                st.session_state.selected_tier = title
                st.rerun()

        # --- 2. RENDER THE PRICING SECTION ---
        st.markdown("<br><br>## 💎 Flexible Tiered Membership Access", unsafe_allow_html=True)
        st.write("Pick the right account pace for your regular revisions.")

        col_free, col_basic, col_prem = st.columns(3)

        # Define the full feature lists here to ensure nothing is missing
        with col_free:
            render_tier_card("Mwalimu AI Free", "Basic daily study toolkit", [
                "10 AI Questions / day", 
                "5 Assessment Quizzes / day", 
                "10 Flashcards generated / day", 
                "Basic Curriculum Notes", 
                "<span style='color: #ef4444;'>❌ No Voice Tutor access</span>", 
                "<span style='color: #ef4444;'>❌ No Custom Study Plans</span>"
            ], "#1e293b")

        with col_basic:
            render_tier_card("Mwalimu AI Plus", "Enhanced daily study toolkit", [
                "50 AI Questions / day", 
                "15 Assessment Quizzes / day", 
                "50 Flashcards generated / day", 
                "Basic Curriculum Notes", 
                "Personalized Study Plans", 
                "<span style='color: #ef4444;'>❌ No Voice Tutor access</span>"
            ], "#1e593c")

        with col_prem:
            render_tier_card("Mwalimu AI Premium", "Complete school execution dashboard", [
                "<b>Unlimited</b> AI Interactive Prompts", 
                "<b>Unlimited</b> targeted CBC Quizzes", 
                "<b>Unlimited</b> Flashcards & Flash summaries", 
                "🎙️ <b>Full Voice Tutor Mode Enabled</b>", 
                "🗓️ Personalized daily Study Plans", 
                "📊 Advanced Analytics & Weak-Topic Detection", 
                "💸 Integrated mobile checkouts"
            ], "#1e3a8a")

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
        