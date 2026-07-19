import streamlit as st
from services.ai import generate_lesson, ask_mwalimu
from services.lms_service import complete_student_lesson, load_course_structure, get_student_lesson_progress

def render_active_lesson_workspace():
    """Renders the comprehensive, linear classroom guide for the student's active lesson."""
    student_profile = st.session_state.get("user_profile", {})
    uid = st.session_state.get("uid")
    grade = st.session_state.get("grade", "Grade 6")
    subject = st.session_state.get("active_subject", "Mathematics")
    
    # Read the active lesson node configuration from state tracking variables
    active_lesson = st.session_state.get("lms_active_lesson_node")
    if not active_lesson:
        st.warning("Please select a subject or topic from the dashboard to begin learning.")
        if st.button("⬅ Return to Dashboard"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
        return

    lesson_id = active_lesson["lesson_id"]
    lesson_title = active_lesson["title"]
    lesson_chat_history_key = f"chat_history_{lesson_id}"

    # =====================================================================   
    # 🏛️ STEP 1: POLISHED TOP HEADER & LESSON CONTEXT BANNER
    # =====================================================================
    # 1. Custom CSS styling to cleanly align headers and cards vertically
    st.markdown("""
    <style>
        .custom-header-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            width: 100%;
        }
        .curriculum-banner {
            background-color: #1E293B;
            border-left: 4px solid #3B82F6;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 24px;
            color: #E2E8F0;
            font-size: 14px;
        }
        .milestone-card {
            background-color: #2F3037;
            border: 1px solid #424656;
            border-radius: 12px;
            padding: 16px;
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

   

    # 3. Balanced Layout Split for Title vs Action Card
    col_header_left, col_header_right = st.columns([1.5, 1], gap="large")

    with col_header_left:
        st.markdown(f"<h1 style='margin-bottom: 4px; padding-top: 0;'>📖 {lesson_title}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='color: #9CA3AF; font-size: 15px; margin-bottom: 16px;'>{subject} &mdash; Grade {grade} | Focus Framework Unit</p>", unsafe_allow_html=True)
        
        if st.button("⬅ Exit to Main Dashboard", type="secondary"):
            st.session_state.current_page = "Main Chat"
            st.rerun()

    with col_header_right:
        # Beautifully structured interactive milestone box card wrapper
        st.markdown("""
        <div class="milestone-card">
            <span style="font-size: 15px; font-weight: 700; color: #ECECF1; display: flex; align-items: center; gap: 6px;">🎯 Complete Lesson Milestone</span>
            <p style="font-size: 13px; color: #9CA3AF; margin: 6px 0 14px 0; line-height: 1.4;">Finished studying the text below? Test your knowledge to unlock the next concept level!</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Pull button right below the stylized card matching container width rules
        if st.button("📝 Start Practice Quiz", type="primary", use_container_width=True):
            st.session_state.lms_active_lesson_node = active_lesson
            st.session_state.workspace_quiz_topic = active_lesson["title"]
            st.session_state.active_subject = subject
            st.session_state.active_grade = grade
            st.session_state.current_page = "Generators Hub"
            st.session_state.active_generator_tab = "Quizzes"
            st.rerun()

    st.write("##")
    st.write("---")


    # =====================================================================
    # 📋 STEP 2: FULL-WIDTH CORE LESSON TEXT
    # =====================================================================
    st.subheader("📋 1. Core Lesson Text")
    
    lesson_cache_key = f"lesson_text_data_{lesson_id}_{uid}"
    if lesson_cache_key not in st.session_state:
        with st.spinner("Mwalimu AI is preparing your custom CBC lesson plan summary..."):
            try:
                lesson_profile = {**student_profile, "subject": subject, "sub_topic": lesson_title}
                raw_lesson_stream = generate_lesson(lesson_title, lesson_profile)
                lesson_text = "".join([chunk if isinstance(chunk, str) else "" for chunk in (raw_lesson_stream or [])])
                st.session_state[lesson_cache_key] = lesson_text
            except Exception as e:
                st.session_state[lesson_cache_key] = f"Could not load lesson contents. Details: {e}"

    st.markdown(st.session_state[lesson_cache_key])
    st.write("---")

    # =====================================================================
    # 💬 STEP 3: FULL-WIDTH CHAT WITH MWALIMU SECTION
    # =====================================================================
    st.write("### 💬 Chat with Mwalimu")
    st.write("Struggling with any paragraphs above? Ask your teacher for simple steps directly below.")
    
    if lesson_chat_history_key not in st.session_state:
        st.session_state[lesson_chat_history_key] = [
            {"role": "assistant", "content": f"Hello! I am reading your lesson notes on '{lesson_title}'. Ask me any questions!"}
        ]
        
    assistant_messages_count = sum(1 for m in st.session_state[lesson_chat_history_key] if m["role"] not in ["student", "user"])
    current_ai_index = 0

    # Display using your exact custom layout bubbles across the full width of the main canvas
    for msg in st.session_state[lesson_chat_history_key]:
        if msg.get("is_voice") == 1:
            continue
            
        if msg["role"] in ["student", "user"]:
            # 👤 STUDENT BUBBLE CONTAINER
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 20px; width: 100%;">
                <div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="text-align: left;">{msg["content"]}</div>
                </div>
                <div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    👤
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            current_ai_index += 1
            id_tag = f"lesson_msg_{current_ai_index}"

            # 👨‍🏫 MWALIMU AI CONTAINER
            st.markdown(f"""
            <div id="{id_tag}" style="display: flex; justify-content: flex-start; align-items: center; gap: 10px; margin-bottom: 12px; width: 100%; scroll-margin-top: 80px;">
                <div style="width: 32px; height: 32px; background-color: #FF4B4B; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    👨‍🏫
                </div>
                <div style="font-family: sans-serif; font-size: 13px; font-weight: 600; color: #FF4B4B; text-transform: uppercase; letter-spacing: 0.5px;">
                    Mwalimu AI
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(msg["content"])
            st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

    # 🛠️ SCROLL ENGINE AUTOMATION MANAGER
    target_scroll_id = f"lesson_msg_{assistant_messages_count}"
    if st.session_state.get("new_message") and assistant_messages_count > 0:
        st.session_state.new_message = False
        st.html(f"""
            <script>
                setTimeout(() => {{
                    const element = window.parent.document.getElementById("{target_scroll_id}");
                    if (element) {{
                        element.scrollIntoView({{ behavior: "smooth", block: "start" }});
                    }}
                }}, 150);
            </script>
        """)

    # Padding to prevent the sticky input field from blocking the last message bubble
    st.markdown("<div style='margin-bottom: 100px;'></div>", unsafe_allow_html=True)

    # =====================================================================
    # ⌨️ STEP 4: GLOBAL CHAT INPUT WINDOW LOCKED AT THE BOTTOM OF THE PAGE
    # =====================================================================
    if user_query := st.chat_input("Ask a question about this lesson...", key="global_lesson_chat_input"):
        st.session_state[lesson_chat_history_key].append({"role": "user", "content": user_query})
        st.session_state.new_message = True
        
        chat_profile = {**student_profile, "subject": subject, "topic": lesson_title, "sub_topic": lesson_title}
        lesson_context_text = st.session_state.get(lesson_cache_key, "")
        adaptive_notes = f"This conversation is locked directly to helping the student understand the following lesson content block: {lesson_context_text[:1200]}"
        
        try:
            response_stream = ask_mwalimu(
                question=user_query,
                student=chat_profile,
                messages=st.session_state[lesson_chat_history_key],
                adaptive_context=adaptive_notes
            )
            assistant_text = "".join([chunk if isinstance(chunk, str) else "" for chunk in response_stream])
            st.session_state[lesson_chat_history_key].append({"role": "assistant", "content": assistant_text})
        except Exception as chat_err:
            st.session_state[lesson_chat_history_key].append({"role": "assistant", "content": f"Brief connection ripple: {chat_err}"})
            
        st.rerun()
        # ====================================================================
    # 🏫 TEACHER GRADEBOOK & LEARNING ANALYTICS WORKSPACE
    # ====================================================================
    st.write("---")
    st.subheader("🏫 Live Classroom Gradebook & Progress Metrics")
    st.write("Monitor curriculum completion velocities and assignment scores across your active student list.")

    from services.database import get_all_student_lms_progress
    gradebook_records = get_all_student_lms_progress()

    if not gradebook_records:
        st.info("No student progress metrics recorded in the database ledger yet.")
        return

    # Convert SQLite rows cleanly to a visual tracking table layout
    gradebook_list = []
    for record in gradebook_records:
        # Convert raw lesson database slugs back to user-friendly titles
        raw_lesson_id = record["lesson_id"]
        clean_lesson_title = str(raw_lesson_id).replace("_", " ").title() if raw_lesson_id else "N/A (Not Started)"
        
        gradebook_list.append({
            "Student Name": record["student_name"],
            "Grade Level": record["student_grade"],
            "Active Subject": record["subject"] or "N/A",
            "Current Topic Unit": clean_lesson_title,
            "LMS Progress Status": record["status"] or "Not Started",
            "Quiz High Score": f"{record['quiz_high_score']}%" if record["quiz_high_score"] is not None else "0%",
            "Completion Date": record["completed_at"] or "In Progress ⏳"
        })

    # Render a high-utility native data frame with wide optimization filters
    st.dataframe(
        gradebook_list,
        use_container_width=True,
        column_config={
            "LMS Progress Status": st.column_config.SelectboxColumn(
                "Status",
                options=["Not Started", "Learning", "Completed"],
                required=True,
            ),
            "Quiz High Score": st.column_config.ProgressColumn(
                "Top Assignment Score",
                format="%s",
                min_value=0,
                max_value=100,
            )
        }
    )
