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
    # UNIFIED ID RESOLUTION
    # ============================================================
    target_uid = st.session_state.get("uid")
    
    if not target_uid:
        st.error("Authentication track parameter missing. Please sign out and sign back in.")
        st.stop()

    user_doc_ref = db.collection("users").document(str(target_uid))
    
    # Fetch live snapshot directly from Firestore
    try:
        doc_snap = user_doc_ref.get()
        db_profile = doc_snap.to_dict() if doc_snap.exists else {}
    except Exception:
        db_profile = {}

    # Fallback to active session profile dictionary memory
    if not db_profile:
        db_profile = st.session_state.get("user_profile") or {}

    # ============================================================
    # 🚨 ISOLATION LAYER: CREATE A DETACHED COPY FOR THE FORM
    # ============================================================
    # This prevents typing inside the fields from mutating the live sidebar state prematurely!
    if "form_temp_profile" not in st.session_state or st.button("🔄 Reset Form Fields", help="Click to pull latest database data"):
        st.session_state.form_temp_profile = {
            "name": db_profile.get("name", st.session_state.get("student_name", "Student")),
            "grade": db_profile.get("grade", st.session_state.get("grade", "Grade 1")),
            "age": int(db_profile.get("age", st.session_state.get("age", 12)))
        }

    # 🚨 CRITICAL PYLANCE ASSURANCE: Guarantees user_doc_ref is evaluated as non-None
    assert user_doc_ref is not None
    
    # ============================================================
    # FLAT UI FORM RENDERING (USES DETACHED ISOLATED MEMORY PATHS)
    # ============================================================
    with st.container(border=True):
        input_name = st.text_input(
            "Student Name", 
            value=st.session_state.form_temp_profile["name"]
        )
        st.text_input(
            "Registered Email Address", 
            value=db_profile.get("email", st.session_state.get("user_email", "")), 
            disabled=True
        )                
        
        new_name = str(input_name).strip() if input_name is not None else ""
        if not new_name:
            st.error("Student Name cannot be left blank.")

        grades_list = [f"Grade {i}" for i in range(1, 13)]
        saved_grade = st.session_state.form_temp_profile["grade"]
        
        try:
            default_grade_index = grades_list.index(saved_grade)
        except ValueError:
            default_grade_index = 0
            
        new_grade = st.selectbox(
            "Current Grade Level", 
            grades_list, 
            index=default_grade_index
        )
        
        new_age = st.number_input(
            "Age", 
            min_value=5, 
            max_value=25, 
            value=st.session_state.form_temp_profile["age"]
        )
        
        # Keep our transient form track updated behind the scenes safely without affecting the sidebar layout
        st.session_state.form_temp_profile["name"] = new_name
        st.session_state.form_temp_profile["grade"] = new_grade
        st.session_state.form_temp_profile["age"] = int(new_age)

        st.warning("""
        ⚠️ **Important Progress Notice:**
        Changing your current grade level or age parameters will reset active quiz metrics and your Learning Progress Data.
        """)
        
        confirm_reset = st.checkbox("I understand and authorize Mwalimu AI to re-align my progress tracking records to this configuration.", key="form_reset_verify")
        
        # ============================================================
        # COMMIT POINT: EXECUTE LIVE UPDATES ONLY ON BUTTON CLICK
        # ============================================================
        if st.button("Save Profile Settings", use_container_width=True, type="primary", key="save_profile_action_node"):
            if not new_name:
                st.error("Please provide a valid Student Name before saving.")
            elif not confirm_reset:
                st.error("Please acknowledge the progress re-alignment warning checkbox above before saving modifications.")
            else:
                with st.spinner("Synchronizing your parameters securely across cloud database nodes..."):
                    
                    # Construct uniform layout map payload configuration
                    payload = {
                        "name": new_name,
                        "grade": new_grade,
                        "age": int(new_age),
                        "email": st.session_state.get("user_email", db_profile.get("email", ""))
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
                    
                    # C. NOW WE SAFELY COMMIT TO THE SIDEBAR LAYER CODES!
                    from services.profile_service import set_student_profile
                    set_student_profile(payload)
                    
                    # D. THE INSTANT DELAY CORRECTION: Clear database caches
                    from services.database import flush_all_database_caches
                    flush_all_database_caches()
                    
                    # E. Keep local persistent browser storage session cookie file wrapper synchronized
                    try:
                        from services.session_service import update_session
                        update_session()
                    except Exception:
                        pass

                    # Clean our temporary storage states right after success
                    if "form_temp_profile" in st.session_state:
                        del st.session_state["form_temp_profile"]

                    st.toast("🎉 Profile settings synchronized successfully!")
                    
                    # F. Force complete application code runtime reload iteration from scratch
                    st.rerun()
