import streamlit as st
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


db = firestore.client()


def render():  
    st.markdown("---")
    if st.button("⬅ Back to Main Chat Dashboard", use_container_width=True):
        st.switch_page(st.session_state.ROUTE_CHAT)
        
    st.subheader("⚙ Edit Student Profile")
    st.write("Keep your academic milestones up to date. Changing your profile details or baseline grade helps Mwalimu AI adjust the difficulty of quizzes and voice tasks automatically.")

    name = st.session_state.get("student_name", "")
    grade = st.session_state.get("grade", "")
    age = st.session_state.get("age", "")
    student = st.session_state.get("student_name", "")
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
                        # Reload the latest profile directly from Firestore
                        updated_profile = user_doc_ref.get().to_dict() or {}

                        # Replace the entire cached profile
                        st.session_state.user_profile = updated_profile

                        # Keep convenience variables synchronized
                        st.session_state.student_name = updated_profile.get("name", safe_name.strip())
                        st.session_state.grade = updated_profile.get("grade", new_grade)
                        st.session_state.age = int(updated_profile.get("age", new_age))
                        st.session_state.user_email = updated_profile.get(
                            "email",
                            st.session_state.get("user_email", "")
                        )
                            
                        st.toast("🎉 Profile settings synchronized successfully!")
                        st.switch_page(st.session_state.ROUTE_CHAT)
                        st.rerun()

    else:
        st.error("Unable to load active profile registry parameters from database data stores.")