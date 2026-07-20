import streamlit as st
import sqlite3
from services.database import DATABASE_NAME
from services.lms_service import complete_student_lesson, unlock_next_lesson

def evaluate_quiz_submission(correct_answers: int, total_questions: int):
    """
    Computes final grading percentages and dynamically coordinates database 
    LMS state updates across both local progress tables and national leaderboards [INDEX].
    """
    if total_questions <= 0:
        return
        
    score_percentage = int((correct_answers / total_questions) * 100)
    
    # Extract keys safely from the standard user tracking profile dictionary
    active_node = st.session_state.get("lms_active_lesson_node")
    user_profile = st.session_state.get("user_profile", {})
    
    if active_node:
        # 🌟 CRUCIAL SYNC: Ensure we grab the identical token matching your 's.id' key syntax
        student_uid = str(st.session_state.get("uid") or user_profile.get("id") or "")
        grade_level = str(user_profile.get("grade") or st.session_state.get("grade", "Grade 6"))
        active_sub = str(st.session_state.get("active_subject") or user_profile.get("subject", "Mathematics"))
        lesson_id = str(active_node.get("lesson_id"))
        
        if score_percentage >= 70:
            # ----------------------------------------------------
            # 🛠️ NATIVE DIRECT DOUBLE-WRITE INTO SQLITE LEDGER
            # ----------------------------------------------------
            # This locks the score metrics so both tables render it immediately
            try:
                from datetime import datetime
                conn = sqlite3.connect(DATABASE_NAME)
                cursor = conn.cursor()
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                cursor.execute("""
                    INSERT INTO student_progress (student_uid, grade, subject, lesson_id, mastery_score, status, quiz_high_score, completed_at)
                    VALUES (?, ?, ?, ?, ?, 'Completed', ?, ?)
                    ON CONFLICT(student_uid, subject, lesson_id) 
                    DO UPDATE SET 
                        mastery_score = MAX(mastery_score, EXCLUDED.mastery_score),
                        quiz_high_score = MAX(quiz_high_score, EXCLUDED.quiz_high_score),
                        status = 'Completed',
                        completed_at = COALESCE(completed_at, EXCLUDED.completed_at)
                """, (student_uid, grade_level, active_sub, lesson_id, score_percentage, score_percentage, now_str))
                
                conn.commit()
                conn.close()
            except Exception as db_write_err:
                print(f"[LMS Evaluator Warning] Direct ledger logging skipped: {db_write_err}")

            # 2. Fire the secondary lms service routines to handle tracking updates safely
            complete_student_lesson(
                student_uid=student_uid,
                grade=grade_level,
                subject=active_sub,
                lesson_id=lesson_id,
                mastery=score_percentage,
                quiz_score=score_percentage
            )
            
            # 3. Unlock the next lesson module node automatically
            unlocked_node = unlock_next_lesson(
                student_uid=student_uid,
                grade=grade_level,
                subject=active_sub,
                current_lesson_id=lesson_id
            )
            
            # Post transaction token balance metrics updates (Keep your existing utility tracks)
            try:
                # If your MwalimuDBService is used to increment daily balances, call it here:
                # from services.database import MwalimuDBService
                # MwalimuDBService.increment_usage(student_uid, "quizzes_taken")
                pass
            except Exception:
                pass
                
            st.balloons()
            st.success(f"🎉 **Mastery Achieved!** You scored {score_percentage}% on your quiz!")
            
            if unlocked_node:
                st.markdown(f"🔓 **Next Unit Unlocked:** You can now proceed to study **'{unlocked_node['title']}'**!")
            else:
                st.markdown("🏆 **Congratulations!** You have officially completed the final lesson unit for this course!")
                
            if st.button("🔄 Return to Dashboard Hub", width="stretch", key="lms_evaluator_return_home_btn"):
                st.session_state.current_page = "Main Chat"
                st.rerun()
        else:
            st.warning(
                f"🎯 **Score: {score_percentage}%** — To unlock the next lesson, "
                f"Mwalimu requires a baseline mastery score of **70% or higher**. "
                f"Go back to your lesson notes, chat with Mwalimu AI, and try again!"
            )
            if st.button("📖 Return to Lesson Review Notes", width="stretch", key="lms_evaluator_retry_notes_btn"):
                st.session_state.current_page = "LMS Lesson Workspace"
                st.rerun()
