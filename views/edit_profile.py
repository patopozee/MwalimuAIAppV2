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
    # UNIFIED ID RESOLUTION (CRITICAL ACCURACY FACTOR)
    # ============================================================
    # Your Firestore uses UID documents universally. We target this path directly.
    target_uid = st.session_state.get("uid")
    
    if not target_uid:
        st.error("Authentication track parameter missing. Please sign out and sign back in.")
        st.stop()

    user_doc_ref = db.collection("users").document(str(target_uid))
    
    # Fetch live snapshot directly from the uniform UID Document reference path
    try:
        doc_snap = user_doc_ref.get()
        active_profile = doc_snap.to_dict() if doc_snap.exists else {}
    except Exception:
        active_profile = {}

    # Fallback to active session profile dictionary memory if Firestore query exhibits lag
    if not active_profile:
        active_profile = st.session_state.get("user_profile") or {}

    # ============================================================
    # LIVE-SYNC WIDGET CALLBACK UTILITIES
    # ============================================================
    def sync_name_live():
        if st.session_state.get("form_input_name"):
            st.session_state.student_name = st.session_state.form_input_name
            if "user_profile" in st.session_state and isinstance(st.session_state.user_profile, dict):
                st.session_state.user_profile["name"] = st.session_state.form_input_name

    def sync_grade_live():
        if st.session_state.get("form_select_grade"):
            st.session_state.grade = st.session_state.form_select_grade
            if "user_profile" in st.session_state and isinstance(st.session_state.user_profile, dict):
                st.session_state.user_profile["grade"] = st.session_state.form_select_grade

    def sync_age_live():
        if st.session_state.get("form_input_age") is not None:
            st.session_state.age = int(st.session_state.form_input_age)
            if "user_profile" in st.session_state and isinstance(st.session_state.user_profile, dict):
                st.session_state.user_profile["age"] = int(st.session_state.form_input_age)

    # 🚨 CRITICAL PYLANCE ASSURANCE: Guarantees user_doc_ref is evaluated as non-None
    assert user_doc_ref is not None
    
    # ============================================================
    # FLAT UI FORM RENDERING (ELIMINATES INTERACTION BLOCKAGES)
    # ============================================================
    with st.container(border=True):
        input_name = st.text_input(
            "Student Name", 
            value=active_profile.get("name", st.session_state.get("student_name", "Student")),
            key="form_input_name",
            on_change=sync_name_live  # Synchronizes sidebar UI header text parameters on key input
        )
        st.text_input(
            "Registered Email Address", 
            value=active_profile.get("email", st.session_state.get("user_email", "")), 
            disabled=True
        )                
        
        new_name = str(input_name).strip() if input_name is not None else ""
        
        if not new_name:
            st.error("Student Name cannot be left blank.")

        grades_list = [f"Grade {i}" for i in range(1, 13)]
        saved_grade = active_profile.get("grade", st.session_state.get("grade", "Grade 1"))
        
        try:
            default_grade_index = grades_list.index(saved_grade)
        except ValueError:
            default_grade_index = 0
            
        new_grade = st.selectbox(
            "Current Grade Level", 
            grades_list, 
            index=default_grade_index,
            key="form_select_grade",
            on_change=sync_grade_live  # Synchronizes navigation headers live when user makes a switch
        )
        
        new_age = st.number_input(
            "Age", 
            min_value=5, 
            max_value=25, 
            value=int(active_profile.get("age", st.session_state.get("age", 12))),
            key="form_input_age",
            on_change=sync_age_live  # Synchronizes workspace metrics array settings instantly
        )
        
        st.warning("""
        ⚠️ **Important Progress Notice:**
        Changing your current grade level or age parameters will reset active quiz metrics and your Learning Progress Data.
        """)
        
        confirm_reset = st.checkbox("I understand and authorize Mwalimu AI to re-align my progress tracking records to this configuration.", key="form_reset_verify")
        
        if st.button("Save Profile Settings", use_container_width=True, type="primary", key="save_profile_action_node"):
            if not new_name:
                st.error("Please provide a valid Student Name before saving.")
            elif not confirm_reset:
                st.error("Please acknowledge the progress re-alignment warning checkbox above before saving modifications.")
            else:
                with st.spinner("Synchronizing your parameters securely across cloud database nodes..."):
                    
                    # Construct explicit dictionary payload configuration map schema
                    payload = {
                        "name": new_name,
                        "grade": new_grade,
                        "age": int(new_age),
                        "email": st.session_state.get("user_email", active_profile.get("email", ""))
                    }
                    
                    # A. Cloud Write Pipeline using exclusive verified user UID index parameter
                    try:
                        user_doc_ref.set(payload, merge=True)
                    except Exception as err:
                        st.error(f"Cloud Storage Connection Interrupted: {str(err)}")
                        st.stop()
                    
                    # B. Wipe performance history collection nodes linked to this verified UID
                    collections_to_wipe = ["quiz_history", "learning_analysis", "quiz_results", "student_progress"]
                    for target_col in collections_to_wipe:
                        try:
                            stale_docs = db.collection(target_col).where(
                                filter=FieldFilter("uid", "==", str(target_uid))
                            ).stream()
                            for doc_item in stale_docs:
                                db.collection(target_col).document(doc_item.id).delete()
                        except Exception:
                            pass
                    
                    # C. Synchronize parameters down through centralized profile manager tool utilities
                    from services.profile_service import set_student_profile
                    set_student_profile(payload)
                    
                    # D. THE INSTANT DELAY CORRECTION: Evict and drop the 120-second memory cache loop
                    from services.database import flush_all_database_caches
                    flush_all_database_caches()
                    
                    # E. Keep local persistent browser storage session cookie file wrapper synchronized
                    try:
                        from services.session_service import update_session
                        update_session()
                    except Exception:
                        pass

                    st.toast("🎉 Profile settings synchronized successfully!")
                    
                    # F. Force complete application code runtime reload iteration from scratch
                    st.rerun()
