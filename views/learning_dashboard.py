import streamlit as st
from services.upgrade_modal import show_upgrade_modal

    
from services.lms_service import (
    get_lms_statistics,
    get_lms_learning_analysis,
    get_lms_quiz_history,
)


def render():
    student_uid = str(st.session_state.get("uid") or "")
    student_grade = str(st.session_state.get("grade", "Grade 6"))
    active_subject = str(st.session_state.get("active_subject", "Mathematics"))
    lms_stats = get_lms_statistics(
        student_uid,
        student_grade,
        active_subject
    )
    from services.lms_service import (
        get_current_active_lesson,
        load_course_structure,
        get_student_lesson_progress,
    )

    #=========
    # # 🏫 LMS CORE INTEGRATION: TODAY'S LEARNING & CONTINUE LEARNING GATE
    # # ====================================================================               
        
    # 1. Unpack subscription details
    student_profile_dict = st.session_state.get("user_profile", {})    
    subscription_tree = student_profile_dict.get('subscription', {}) if isinstance(student_profile_dict.get('subscription'), dict) else {}
    user_tier = str(subscription_tree.get('tier', 'Free')).strip()

    if "premium" in user_tier.lower() or "plus" in user_tier.lower():
        st.session_state.lms_limit_reached = False

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
                if st.button("🚀 Continue Learning", key="lms_dash_continue_learning_action_btn", use_container_width=True, type="primary"):
                    
                    if not ("premium" in user_tier.lower() or "plus" in user_tier.lower()):
                        st.session_state.lms_limit_reached = True
                        st.rerun()
                    else:
                        st.session_state.pop("lms_limit_reached", None)
                        st.session_state.lms_active_lesson_node = current_lesson
                        st.session_state.active_subject = active_subject 
                        
                        # SWITCH PAGES NATIVELY WITH THE NAVIGATION SLUG 🚀
                        if "ROUTE_LESSON" in st.session_state:
                            st.switch_page(st.session_state.ROUTE_LESSON)


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
                
    st.markdown("## 📈 Learning Statistics")
    with st.container(border=True):
        st.write("Learning statistics coming here...")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Average Score",
                f"{lms_stats['average_score']}%"
            )

        with col2:
            st.metric(
                "Lessons",
                f"{lms_stats['completed_lessons']}/{lms_stats['total_lessons']}"
            )

        with col3:
            st.metric(
                "Completion",
                f"{lms_stats['completion']}%"
            )

        with col4:
            st.metric(
                "Mastery",
                f"{lms_stats['mastery']}%"
            )
    st.markdown("---")

    st.subheader("📊 Performance Trend")

    # 🎯 FIXED: Removed the incorrect 3-argument function call and kept only the valid lms history call
    history_scores = get_lms_quiz_history(
        student_uid,
        active_subject
    )

    if history_scores:
        st.line_chart(history_scores)
    else:
        st.info("Complete LMS lessons to see your performance trend.")

    analysis = get_lms_learning_analysis(
        student_uid,
        active_subject
    )

    left, right = st.columns(2)

    with left:
        with st.expander(
            f"❌ Needs Improvement ({len(analysis['weak_topics'])})",
            expanded=False
        ):
            if analysis["weak_topics"]:
                for topic in analysis["weak_topics"]:
                    st.markdown(f"• {topic}")
            else:
                st.success("No weak topics 🎉")

    with right:
        with st.expander(
            f"✅ Mastered Areas ({len(analysis['strong_topics'])})",
            expanded=False
        ):
            if analysis["strong_topics"]:
                for topic in analysis["strong_topics"]:
                    st.markdown(f"• {topic}")
            else:
                st.info("Complete lessons to unlock mastery.")