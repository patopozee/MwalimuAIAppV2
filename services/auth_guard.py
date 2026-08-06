# import streamlit as st
# from services.session_service import validate_session
# from services.database import get_student_data # Use your exact file path here

# def enforce_authentication():
#     """Call this at the absolute top line of every single sub-page file."""
    
#     # 1. Initialize checking keys if missing
#     if "session_checked" not in st.session_state:
#         st.session_state.session_checked = False
#     if "user_authenticated" not in st.session_state:
#         st.session_state.user_authenticated = False

#     # 2. Try to restore session from the cookie container
#     if not st.session_state.user_authenticated and not st.session_state.session_checked:
#         session_data = validate_session()
        
#         if session_data is not None:
#             uid = session_data["uid"]
#             profile = get_student_data(uid)
            
#             if profile:
#                 st.session_state.user_authenticated = True
#                 st.session_state.uid = uid
#                 st.session_state.user_email = profile.get("email", session_data["email"])
#                 st.session_state.student_name = profile.get("name", "Student")
#                 st.session_state.grade = profile.get("grade", "Grade 1")
#                 st.session_state.age = int(profile.get("age", 10))
#                 st.session_state.user_profile = profile
#                 st.session_state.session_checked = True
#                 st.toast(f"🔄 Session restored!")
#                 st.rerun()
#         else:
#             st.session_state.session_checked = True
            
#             # FIX: Instead of st.stop(), switch back to your entry point script file
#             st.switch_page("main.py") 

#     # 3. Guard against direct URL entry if cookie authentication checks failed
#     if not st.session_state.user_authenticated:
#         st.switch_page("main.py")
