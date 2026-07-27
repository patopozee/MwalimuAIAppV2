import streamlit as st
import re
import json
import ast
from services.upgrade_modal import show_upgrade_modal
from services.tier_guard import verify_tier_allowance
from services.ai import ask_mwalimu, generate_quiz, generate_study_plan, generate_flashcards, generate_lesson
from services.db_service import MwalimuDBService
from services.upgrade_modal import show_upgrade_modal
from services.quiz_evaluator import evaluate_quiz_submission
from services.database import (
    save_activity,
    get_student_stats,
    get_next_difficulty,
    get_student_data  #  ADD THIS LINE HERE
)

def render(): 
    # 🚀 FIX: Pull the authoritative active profile dictionary from the sidebar state store
    if "active_student_profile" in st.session_state:
        student = st.session_state.active_student_profile
    else:
        # Secure structural fallback mapping properties if missing
        student = {
            "name": st.session_state.get("student_name", "Student"),
            "grade": st.session_state.get("grade", "Grade 6"),
            "age": int(st.session_state.get("age", 12)) if st.session_state.get("age") else 12,
            "language": st.session_state.get("language", "English"),
            "preferred_language": st.session_state.get("language", "English"),
            "subject": st.session_state.get("active_subject", "Science and Technology"),
            "topic": st.session_state.get("active_topic", ""),
            "sub_topic": st.session_state.get("active_sub_topic", ""),
            "learning_outcome": st.session_state.get("active_learning_outcome", "General")
        }

    # Extract baseline layout pointers
    subject = student.get("subject", "")
    sub_topic = student.get("sub_topic", "")
    learning_outcome = student.get("learning_outcome", "")


    st.markdown("---")
    st.subheader("🎯 Mwalimu AI Learning Generators Hub")
    st.write(f"Active Context: **{student['subject']}** ➡️ **{student['topic']}** ({student['language']})")

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
    user_tier = str(raw_tier).strip()
    uid = str(st.session_state.get("uid") or st.session_state.user_email)

    # Initialize global layout state variables if missing
    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "flashcards" not in st.session_state:
        st.session_state.flashcards = None
    if "lesson_content" not in st.session_state:
        st.session_state.lesson_content = None

    # Build Interactive Workspace Tabs Container
    tab_quiz, tab_flash, tab_less, tab_plan = st.tabs(["📝 Quiz Generator", "🗂️ Flashcards Maker", "📖 Lesson Planner", "📅 Study Plan"])

    # ==========================================
    # --- 1. QUIZ GENERATOR TAB (TIER GUARDED) ---
    # ==========================================
    with tab_quiz:
        st.subheader("Quiz Generator")

        # Get the active lesson FIRST
        active_lesson = st.session_state.get("lms_active_lesson_node")

        # 1. Determine what the active topic should be based on your context logic
        if active_lesson:
            computed_topic = active_lesson.get("title", "")
        else:
            # If the user typed something else manually, preserve it; otherwise fall back to sub_topic
            computed_topic = st.session_state.get("workspace_quiz_topic", sub_topic)

        # 2. Force update session state when the active context changes
        if "workspace_quiz_topic" not in st.session_state or active_lesson:
            st.session_state["workspace_quiz_topic"] = computed_topic
        elif st.session_state.get("last_sub_topic") != sub_topic and not active_lesson:
            # This ensures that if the sidebar subbox changes, the quiz topic updates automatically
            st.session_state["workspace_quiz_topic"] = sub_topic
            st.session_state["last_sub_topic"] = sub_topic

        # 3. Render the text input safely WITHOUT the 'value=' conflict parameter
        raw_quiz_input = st.text_input(
            "Quiz Topic",
            key="workspace_quiz_topic"
        )

        quiz_topic: str = str(raw_quiz_input).strip() if raw_quiz_input else ""

        
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
        
        # Normalize user_tier to match your tier guard system (Pylance Typecast Fix)
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
            if 'show_upgrade_modal' in globals():
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
                    
                    # 🎯 PASS CORRECTING CONTEXT: Use 'student' dict to send preferred_language and subject parameters
                    active_context = dict(student if 'student' in locals() else student_profile)

                    # Synchronize the context with the active lesson
                    active_context["sub_topic"] = quiz_topic
                    active_context["topic"] = quiz_topic
                    quiz_result = generate_quiz(quiz_topic, active_context, target_diff)
                    
                    if quiz_result:
                        st.session_state.quiz = quiz_result
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_raw_score = 0
                        
                        MwalimuDBService.increment_usage(uid, "quizzes")
                        
                        if not verify_tier_allowance(uid, user_tier, "quizzes"):
                            st.session_state.quiz_limit_reached = True
                        
                            save_activity(
                                student_uid=str(st.session_state.get("uid", "")), # 🌟 FIXED: Pass the active student UID string
                                student_name=name,
                                student_grade=grade,
                                student_age=age_int,
                                activity_type="quiz_generation",
                                topic=quiz_topic,
                                score=0,
                                subject=subject,
                                topics=quiz_topic,
                                sub_topic=quiz_topic,
                                learning_outcome=student.get("learning_outcome", "General") if 'student' in locals() else "General"
                            )

                        st.rerun()

        # ----------------------------------------------------
        # 🎯 DYNAMIC LOCALIZATION LABELS FOR FRONTEND VIEW
        # ----------------------------------------------------
        current_lang = student.get("preferred_language", "English") if 'student' in locals() else "English"
        is_swahili = "swahili" in str(current_lang).lower()
        
        label_q_prefix = "Swali" if is_swahili else "Question"
        label_choice_title = "Chagua jibu:" if is_swahili else "Choose your answer:"
        label_warning_unanswered = "Tafadhali jibu maswali yote kabla ya kuwasilisha." if is_swahili else "Please answer all questions before submitting."

        # ----------------------------------------------------
        # Render Active Quiz Layout (Stays open across user interactions)
        # ----------------------------------------------------
        # ----------------------------------------------------
        # Render Active Quiz Layout (Defensive Structure Fix)
        # ----------------------------------------------------
        # ----------------------------------------------------
        # Render Active Quiz Layout (Full Complete Fix)
        # ----------------------------------------------------
        if st.session_state.quiz:
            quiz_data = []
            clean_str = "" 
            
            try:
                raw_json = st.session_state.quiz
                if isinstance(raw_json, str):
                    clean_str = str(raw_json).strip()
                    if clean_str.startswith("```json"):
                        clean_str = clean_str.replace("```json", "", 1).rstrip("`").strip()
                    elif clean_str.startswith("```"):
                        clean_str = clean_str.replace("```", "", 1).rstrip("`").strip()
                    
                    clean_str = re.sub(r'\[\s*=\s*"', '["', clean_str)
                    clean_str = re.sub(r',\s*=\s*"', ',"', clean_str)
                    
                    parsed_data = json.loads(clean_str)
                else:
                    parsed_data = raw_json
                    
                if isinstance(parsed_data, dict):
                    quiz_data = parsed_data.get("quiz", parsed_data.get("questions", []))
                elif isinstance(parsed_data, list):
                    quiz_data = parsed_data
                    
            except Exception as parse_error:
                try:
                    clean_ast = clean_str.replace("true", "True").replace("false", "False").replace("null", "None")
                    parsed_data = ast.literal_eval(clean_ast)
                    if isinstance(parsed_data, dict):
                        quiz_data = parsed_data.get("quiz", parsed_data.get("questions", []))
                    elif isinstance(parsed_data, list):
                        quiz_data = parsed_data
                except Exception:
                    quiz_data = []

            # 1. RENDER QUESTIONS
            if isinstance(quiz_data, list) and len(quiz_data) > 0:
                st.markdown("### Generated Quiz")
                for i, question in enumerate(quiz_data):
                    st.markdown(f"#### {label_q_prefix} {i+1}")
                    raw_opts = question.get("options", [])
                    options_list = list(raw_opts.values()) if isinstance(raw_opts, dict) else raw_opts
                    
                    st.radio(
                        question.get("question", "No question text"),
                        options_list,
                        index=None,
                        key=f"q_{i}",
                        disabled=st.session_state.get("quiz_submitted", False)
                    )

                st.markdown("<br>", unsafe_allow_html=True)

                # 2. SUBMIT HANDLING BLOCK (Brings back your missing button!)
                if not st.session_state.get("quiz_submitted", False):
                    submit_label = "Tuma Maswali" if is_swahili else "Submit Quiz"
                    if st.button(submit_label, use_container_width=True):
                        current_answers = [st.session_state.get(f"q_{i}") for i in range(len(quiz_data))]
                        if None in current_answers:
                            st.warning(label_warning_unanswered)
                        else:
                            score = 0
                            for i, q in enumerate(quiz_data):
                                if current_answers[i] == q.get("answer"):
                                    score += 1
                            
                            total_questions = len(quiz_data)
                            st.session_state.quiz_raw_score = score
                            st.session_state.quiz_score = round((score / total_questions) * 100)
                            st.session_state.quiz_submitted = True
                            
                            evaluate_quiz_submission(correct_answers=score, total_questions=total_questions)
                            
                            save_activity(
                                student_uid=uid,
                                student_name=name,
                                student_grade=grade,
                                student_age=age_int,
                                activity_type="quiz_score",
                                topic=quiz_topic,
                                score=st.session_state.quiz_score,
                                subject=student.get("subject", "General"),
                                topics=student.get("topic", "General"),
                                sub_topic=student.get("sub_topic", "General"),
                                learning_outcome=student.get("learning_outcome", "General")
                            )
                            st.rerun()

                # 3. POST-SUBMISSION REVIEW DISPLAY
                if st.session_state.get("quiz_submitted", False):
                    raw_score = st.session_state.get("quiz_raw_score", 0)
                    total_questions = len(quiz_data)
                    percentage = st.session_state.get("quiz_score", 0)
                    
                    banner_msg = f"🎉 Umepata {raw_score}/{total_questions} ({percentage}%)" if is_swahili else f"🎉 You scored {raw_score}/{total_questions} ({percentage}%)"
                    st.success(banner_msg)
                    
                    review_heading = "### Uhakiki wa Majibu" if is_swahili else "### Answer Review"
                    st.markdown(review_heading)
                    
                    for i, q in enumerate(quiz_data):
                        student_answer = st.session_state.get(f"q_{i}")
                        correct_answer = q.get("answer")
                        st.markdown(f"**{label_q_prefix} {i+1}**")
                        st.write(q.get("question"))
                        
                        answer_label = " Jibu Lako:" if is_swahili else " Your Answer:"
                        correct_label = "Jibu Sahihi:" if is_swahili else "Correct Answer:"
                        st.write(f"*{answer_label}* `{student_answer}`")
                        if student_answer == correct_answer:
                            st.success(f" {correct_label} {correct_answer}")
                        else:
                            st.error(f" {correct_label} {correct_answer}")
                    
                    reset_label = "Futa Matokeo ya Maswali" if is_swahili else "Clear Quiz Results"
                    if st.button(reset_label, use_container_width=True, key="clear_workspace_quiz_results"):
                        st.session_state.quiz = None
                        st.session_state.quiz_submitted = False
                        st.session_state.quiz_score = 0
                        st.session_state.quiz_raw_score = 0
                        if not verify_tier_allowance(uid, user_tier, "quizzes"):
                            st.session_state.quiz_limit_reached = True
                        st.rerun()
            else:
                st.markdown("### Generated Quiz Plan")
                st.info("Mwalimu format description:")
                st.markdown(st.session_state.quiz)


                
                


    # ==========================================
    # --- 2. FLASHCARDS TAB (TIER GUARDED) ---
    # ==========================================
            #=====Flash Card ====
    with tab_flash:
        st.subheader("AI Flashcards Maker")
        
        # Ensure input string extraction can never evaluate as NoneType or throw Pylance errors
        raw_fc_input = st.text_input("Enter a topic for your flashcards:", value=sub_topic if 'sub_topic' in locals() else "", key="fc_topic")
        flashcard_topic: str = str(raw_fc_input).strip() if raw_fc_input else ""
        
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
        if "flashcards" not in st.session_state:
            st.session_state.flashcards = None
            
        has_active_flashcards = st.session_state.flashcards is not None

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
            if 'show_upgrade_modal' in globals():
                show_upgrade_modal()

        # ----------------------------------------------------
        # Flashcards Generation Action Trigger
        # ----------------------------------------------------
        if st.button("Generate Flashcards", use_container_width=True, key="execute_workspace_flashcards"):
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
                    # 🎯 FIX: Pass active contextual 'student' map to respect Subject and preferred_language
                    active_context = student if 'student' in locals() else student_profile
                    fc_result = generate_flashcards(flashcard_topic, active_context)
                    
                    if fc_result:
                        st.session_state.flashcards = fc_result
                        MwalimuDBService.increment_usage(uid, "flashcards")
                        
                        if not verify_tier_allowance(uid, user_tier, "flashcards"):
                            st.session_state.flashcards_limit_reached = True
                        st.rerun()

        # ----------------------------------------------------
        # SAFE DISPLAY & STRUCTURAL JSON PARSING LAYER
        # ----------------------------------------------------
        if st.session_state.flashcards:
            st.info("💡 Click 'Show Answer' to test your active recall memory knowledge!")
            
            try:
                cards_data = st.session_state.flashcards
                
                # Clean and unpack markdown string code block wrappers safely
                if isinstance(cards_data, str):
                    clean_flash = str(cards_data).strip()
                    if clean_flash.startswith("```json"):
                        clean_flash = clean_flash.replace("```json", "", 1).rstrip("`").strip()
                    elif clean_flash.startswith("```"):
                        clean_flash = clean_flash.replace("```", "", 1).rstrip("`").strip()
                    cards_data = json.loads(clean_flash)
                
                # Unroll nested payload mappings gracefully matching all potential AI output types
                if isinstance(cards_data, dict):
                    actual_list = cards_data.get("flashcards", cards_data.get("cards", cards_data.get("questions", [])))
                elif isinstance(cards_data, list):
                    actual_list = cards_data
                else:
                    actual_list = []

                # Draw interactive elements loops safely
                for idx, card in enumerate(actual_list):
                    if isinstance(card, dict):
                        # 🎯 FIX: Check for English AND Swahili key variants generated by the AI
                        q_text = card.get("front", card.get("question", card.get("swali", card.get("mbele", "No question context"))))
                        a_text = card.get("back", card.get("answer", card.get("jibu", card.get("nyuma", "No answer context"))))
                    else:
                        q_text = f"Card Detail Element {idx + 1}"
                        a_text = str(card)

                    st.markdown(f"### Flashcard {idx + 1}")
                    st.write(f"**❓ Question:** {q_text}")
                    
                    with st.expander("👁️ Show Answer"):
                        st.success(f"**💡 Answer:** {a_text}")

                        
            except Exception as parse_error:
                # Absolute emergency string fallback layout to prevent crashes if JSON format breaks
                st.markdown(st.session_state.flashcards)
            
            st.markdown("---")
            if st.button("Clear Flashcards", use_container_width=True, key="clear_workspace_flashcards"):
                st.session_state.flashcards = None
                if not verify_tier_allowance(uid, user_tier, "flashcards"):
                    st.session_state.flashcards_limit_reached = True
                st.rerun()


    
    # ==========================================
    # --- 3. LESSON GENERATOR TAB (TIER GUARDED) ---
    # ==========================================
    with tab_less:
        st.subheader("AI Lessons Generator")
        
        # 🎯 PYLANCE FIX: Protect lesson text input string binding variables from NoneType evaluations
        # If learning_outcome is missing or local context varies, it defaults safely to an empty string
        default_lesson_value = learning_outcome if 'learning_outcome' in locals() and learning_outcome else ""
        raw_lesson_input = st.text_input("Enter the topic you want to learn today:", value=default_lesson_value, key="lesson_topic_input")
        lesson_topic: str = str(raw_lesson_input).strip() if raw_lesson_input else ""
        
        # Fetch student tier profile data upfront using structured backend definitions
        student_profile = get_student_data(st.session_state.user_email) or {}
        subscription = student_profile.get("subscription", {}) if isinstance(student_profile.get("subscription"), dict) else {}
        user_tier = str(subscription.get("tier", "Free")).strip()
        uid = str(st.session_state.get("uid") or st.session_state.user_email)
        
        # Extract baseline metrics for your background firestore activity logging map layers
        name = str(student_profile.get("name", "Student"))
        grade = str(student_profile.get("grade", "General"))
        try:
            age_int = int(student_profile.get("age", 0))
        except (ValueError, TypeError):
            age_int = 0
        
        # Check if there is active lesson content currently displayed on screen safely
        has_active_lesson = "lesson_content" in st.session_state and st.session_state.lesson_content is not None

        # ----------------------------------------------------
        # State-Driven Upgrade Gatekeeper Banner
        # ----------------------------------------------------
        if st.session_state.get("lessons_limit_reached") and not has_active_lesson:
            st.error("⚠️ Lessons Limit Reached, Wait for 24hrs or Upgrade to Premium to continue!")
            
            if st.button("🚀 Upgrade to Premium", key="lesson_upgrade_unique_btn"):
                st.session_state.pop("lessons_limit_reached", None)
                st.session_state.trigger_lesson_upgrade_modal = True
                st.rerun()

        # ----------------------------------------------------
        # Safe Modal Activation Layer (Prevents Continuous Loops)
        # ----------------------------------------------------
        if st.session_state.get("trigger_lesson_upgrade_modal"):
            st.session_state.pop("trigger_lesson_upgrade_modal", None)
            if 'show_upgrade_modal' in globals():
                show_upgrade_modal()

        # ----------------------------------------------------
        # Lessons Generation Action Trigger
        # ----------------------------------------------------
        if st.button("Generate Lesson", use_container_width=True, key="execute_workspace_lessons"):
            if not lesson_topic:
                st.warning("Please enter a valid lesson topic first!")
            elif not name or name == "Student":
                st.warning("Please create Student Profile in the sidebar first!")
            
            # 🎯 1. FIX: Request allowance using the exact plural configuration key
            elif not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                st.session_state.lessons_limit_reached = True
                st.rerun()
            else:
                st.session_state.pop("lessons_limit_reached", None)

                with st.spinner("Mwalimu AI is preparing your personalized lesson..."):
                    try:
                        active_student_context = student if 'student' in locals() else student_profile
                        st.session_state.lesson_content = generate_lesson(lesson_topic, active_student_context)
                        
                        # 🎯 2. FIX: Deduct usage tokens inside the plural "lessons" registry row
                        MwalimuDBService.increment_usage(uid, "lessons")
                        
                        st.session_state.user_profile = None  # Instantly wipe the view profile RAM cache
                        
                        if not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                            st.session_state.lessons_limit_reached = True
                            
                        act_subject = student.get("subject", "General") if 'student' in locals() else "General"
                        act_topic = student.get("topic", "General") if 'student' in locals() else "General"
                        act_sub = student.get("sub_topic", "General") if 'student' in locals() else "General"
                        act_out = student.get("learning_outcome", "General") if 'student' in locals() else "General"

                        # 🎯 3. FIX: Save activity mapping configuration tracking logs as "lessons"
                        save_activity(
                            student_uid=uid,
                            student_name=name, student_grade=grade, student_age=age_int,
                            activity_type="lessons", topic=lesson_topic, score=0,
                            subject=act_subject, topics=act_topic, sub_topic=act_sub, learning_outcome=act_out
                        )
                    except Exception as e:
                        st.error(f"Failed to generate lesson: {str(e)}")
                    st.rerun()


                    
        # ----------------------------------------------------
        # Render Active Lesson Layout (Safe String Backtick Cleaner)
        # ----------------------------------------------------
        if "lesson_content" in st.session_state and st.session_state.lesson_content:
            st.markdown("---")
            st.info("Tip: Read through the breakdown below. Mwalimu customized this explanation precisely for your style!")
            
            raw_lesson = st.session_state.lesson_content
            if raw_lesson and isinstance(raw_lesson, str):
                # 🎯 PYLANCE FIX: Safely wrap string cast evaluations before cleaning block backticks
                safe_lesson: str = str(raw_lesson).strip()
                
                if safe_lesson.startswith("```markdown"):
                    safe_lesson = safe_lesson.replace("```markdown", "", 1).rstrip("`").strip()
                elif safe_lesson.startswith("```"):
                    safe_lesson = safe_lesson.replace("```", "", 1).rstrip("`").strip()
                st.markdown(safe_lesson)
            else:
                st.write(raw_lesson)
                
            if st.button("Clear Lesson Content", use_container_width=True, key="clear_workspace_lessons"):
                st.session_state.lesson_content = None
                
                if not verify_tier_allowance(st.session_state.user_email, user_tier, "lessons"):
                    st.session_state.lessons_limit_reached = True
                st.rerun()
    # =====================================================================
    # --- AI STUDY PLAN TAB
    # =====================================================================
    with tab_plan:
            
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
                    local_metrics = get_student_stats(student["name"], student["grade"], student["age"])
                    # 🎯 FIX: Pass the fully contextual 'student' dictionary instead of 'student_profile'
                    st.session_state.study_plan = generate_study_plan(student, local_metrics)

                    
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
