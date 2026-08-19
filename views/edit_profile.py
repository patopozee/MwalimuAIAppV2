import streamlit as st
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from services.navigation_service import navigate_to

db = firestore.client()

def render():  
    st.markdown("---")
    if st.button("⬅ Back to Main Chat Dashboard", use_container_width=True):
        navigate_to(
            st.session_state.ROUTE_CHAT,
            "Main Chat",
            "main",
        )
        st.rerun()
        
    st.subheader("⚙ Edit Student Profile")
    st.write("Keep your academic milestones up to date. Changing your profile details or baseline grade helps Mwalimu AI adjust the difficulty of quizzes and voice tasks automatically.")

    # ============================================================
    # FIRESTORE DOCUMENT RESOLUTION (FIX FOR GOOGLE AUTH)
    # ============================================================
    uid_key = st.session_state.get("uid")
    email_key = st.session_state.get("user_email")
    
    active_profile = {}
    current_uid = None
    user_doc_ref = None

    # 1. First, try pulling the profile using the unique Firebase UID
    if uid_key:
        user_doc_ref = db.collection("users").document(str(uid_key))
        doc_snap = user_doc_ref.get()
        if doc_snap.exists:
            active_profile = doc_snap.to_dict() or {}
            current_uid = uid_key

    # 2. Fallback: If no document found (common for Google Auth accounts mapped by email)
    if (not active_profile) and email_key:
        user_doc_ref = db.collection("users").document(str(email_key))
        doc_snap = user_doc_ref.get()
        if doc_snap.exists:
            active_profile = doc_snap.to_dict() or {}
            current_uid = email_key

    # 3. Last resort fallback to guarantee active_profile is NEVER None
    if not active_profile:
        active_profile = {}
        current_uid = str(uid_key if uid_key else email_key)
        user_doc_ref = db.collection("users").document(current_uid)

    # 🚨 CRITICAL PYLANCE ASSURANCE: Guarantees user_doc_ref is evaluated as non-None
    assert user_doc_ref is not None
    
    if active_profile or not st.session_state.get("user_authenticated", False):
        with st.container(border=True):
            input_name = st.text_input(
                "Student Name", 
                value=active_profile.get("name", st.session_state.get("student_name", "Student"))
            )
            st.text_input(
                "Registered Email Address", 
                value=active_profile.get("email", st.session_state.get("user_email", "")), 
                disabled=True
            )                
            
            new_name = str(input_name) if input_name is not None else ""
            
            if not new_name.strip():
                st.error("Student Name cannot be left blank.")

            grades_list = [f"Grade {i}" for i in range(1, 13)]
            saved_grade = active_profile.get("grade", st.session_state.get("grade", "Grade 1"))
            
            try:
                default_grade_index = grades_list.index(saved_grade)
            except ValueError:
                default_grade_index = 0
                
            new_grade = st.selectbox("Current Grade Level", grades_list, index=default_grade_index)
            new_age = st.number_input("Age", min_value=5, max_value=25, value=int(active_profile.get("age", st.session_state.get("age", 12))))
            
            st.warning("""
            ⚠️ **Important Progress Notice:**
            Changing your current grade level or age parameters will reset active quiz metrics and your Learning Progress Data.
            """)
            
            confirm_reset = st.checkbox("I understand and authorize Mwalimu AI to re-align my progress tracking records to this new profile configuration.")
            
            if st.button("Save Profile Settings", use_container_width=True, type="primary"):
                safe_name = str(new_name) if new_name is not None else ""
                
                if not safe_name.strip():
                    st.error("Please provide a valid Student Name before saving.")
                elif not confirm_reset:
                    st.error("Please acknowledge the progress re-alignment warning checkbox above before saving modifications.")
                else:
                    with st.spinner("Re-aligning your academic workspace profile..."):
                        # A. Update Firestore
                        user_doc_ref.update({
                            "name": safe_name.strip(),
                            "grade": new_grade,
                            "age": int(new_age)
                        })
                        
                        # B. Clear performance collections matching the resolved UID or Email key
                        collections_to_wipe = ["quiz_history", "learning_analysis", "quiz_results", "student_progress"]
                        for target_col in collections_to_wipe:
                            try:
                                stale_docs = db.collection(target_col).where(
                                    filter=FieldFilter("uid", "==", str(current_uid))
                                ).stream()
                                for doc_item in stale_docs:
                                    db.collection(target_col).document(doc_item.id).delete()
                            except Exception:
                                pass
                        
                        # C. Fetch freshly updated document directly from Firestore
                        profile_snapshot = user_doc_ref.get().to_dict()
                        updated_profile = profile_snapshot if profile_snapshot is not None else {}

                        # D. Synchronize ALL session keys (Flat & Nested) instantly
                        st.session_state.user_profile = updated_profile
                        st.session_state.student_name = updated_profile.get("name", safe_name.strip())
                        st.session_state.grade = updated_profile.get("grade", new_grade)
                        st.session_state.age = int(updated_profile.get("age", new_age))
                        st.session_state.user_email = updated_profile.get("email", st.session_state.get("user_email", ""))
                        
                        # E. Sync persistent session service cookie layer
                        try:
                            from services.session_service import update_session
                            update_session()
                        except Exception:
                            pass

                        st.toast("🎉 Profile settings synchronized successfully!")
                        
                        # F. FORCE IMMEDIATE RERUN
                        st.rerun()

    else:
        st.error("Unable to load active profile registry parameters from database data stores.")
