import streamlit as st
from services.lms_service import complete_student_lesson, unlock_next_lesson

def evaluate_quiz_submission(correct_answers: int, total_questions: int):
    """
    Computes final grading percentages and dynamically coordinates database 
    LMS state updates using standardized key conventions.
    """
    if total_questions <= 0:
        return
        
    score_percentage = int((correct_answers / total_questions) * 100)
    
    # Extract keys safely from the standard user tracking profile dictionary
    active_node = st.session_state.get("lms_active_lesson_node")
    user_profile = st.session_state.get("user_profile", {})
    
    if active_node:
        student_uid = str(st.session_state.get("uid") or "")
        grade_level = str(user_profile.get("grade") or st.session_state.get("grade", "Grade 6"))
        
        # Enforce unified 'subject' naming convention
        active_sub = str(st.session_state.get("active_subject") or user_profile.get("subject", "Mathematics"))
        lesson_id = str(active_node.get("lesson_id"))
        
        if score_percentage >= 70:
            # 1. Update progress ledger
            complete_student_lesson(
                student_uid=student_uid,
                grade=grade_level,
                subject=active_sub,
                lesson_id=lesson_id,
                mastery=score_percentage,
                quiz_score=score_percentage
            )
            
            # 2. Unlock the next lesson module node
            unlocked_node = unlock_next_lesson(
                student_uid=student_uid,
                grade=grade_level,
                subject=active_sub,
                current_lesson_id=lesson_id
            )
            if unlocked_node:
                st.session_state.lms_active_lesson_node = unlocked_node
                
                # Use a pending transition variable instead of hitting the widget key directly
                st.session_state["pending_topic_update"] = unlocked_node["title"]
                
                st.success(f"Next lesson unlocked: {unlocked_node['title']}")
            else:
                st.success("Congratulations! Course completed!")
            
            st.balloons()
            st.success(f"🎉 **Mastery Achieved!** You scored {score_percentage}% on your quiz!")
            
            
            if unlocked_node:
                st.markdown(f"🔓 **Next Unit Unlocked:** You can now proceed to study **'{unlocked_node['title']}'**!")
            else:
                st.markdown("🏆 **Congratulations!** You have officially completed the final lesson unit for this course!")
                
            if st.button("🔄 Return to Dashboard Hub", width="stretch"):
                st.session_state.current_page = "Main Chat"
                st.rerun()
        else:
            st.warning(
                f"🎯 **Score: {score_percentage}%** — To unlock the next lesson, "
                f"Mwalimu requires a baseline mastery score of **70% or higher**. "
                f"Go back to your lesson notes, chat with Mwalimu AI, and try again!"
            )
            if st.button("📖 Return to Lesson Review Notes", width="stretch"):
                st.session_state.current_page = "LMS Lesson Workspace"
                st.rerun()
