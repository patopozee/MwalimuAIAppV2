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
    
            # Pull or cache the generated lesson material using your existing services/ai.py pipeline
    lesson_cache_key = f"lesson_text_data_{lesson_id}_{uid}"
    if lesson_cache_key not in st.session_state:
        with st.spinner("Mwalimu AI is preparing your custom CBC lesson plan summary..."):
            try:
                # Temporary profile adaptions to supply your specific generate_lesson signature
                lesson_profile = {**student_profile, "subject": subject, "sub_topic": lesson_title}
                raw_lesson_stream = generate_lesson(lesson_title, lesson_profile)
                
                # 🚀 COMPILER FIX: Robustly unpack OpenRouter stream data token chunks safely                                  
                compiled_chunks_list = []
                
                if raw_lesson_stream is not None:
                    for chunk in raw_lesson_stream:
                        # 1. Dynamic Attribute Lookup (Prevents Pylance reportAttributeAccessIssue errors)
                        choices = getattr(chunk, 'choices', None)
                        if choices and len(choices) > 0:
                            delta = getattr(choices[0], 'delta', None)
                            if delta:
                                content = getattr(delta, 'content', None)
                                if content:
                                    compiled_chunks_list.append(str(content))
                        
                        # 2. Fallback check if your service file passes dictionary data shapes
                        elif isinstance(chunk, dict) and "choices" in chunk:
                            choices_list = chunk.get("choices", [])
                            if choices_list and len(choices_list) > 0:
                                delta_dict = choices_list[0].get("delta", {})
                                if "content" in delta_dict:
                                    compiled_chunks_list.append(str(delta_dict["content"]))
                                    
                        # 3. Last fallback safeguard configuration parameters
                        elif isinstance(chunk, str):
                            compiled_chunks_list.append(chunk)
                
                # Merge all individual text tokens cleanly into a single long document string
                lesson_text = "".join(compiled_chunks_list).strip()

                
                # 🛡️ SANITIZATION: If the text is empty or falls back to an API check tag, provide a fallback alert
                if not lesson_text or lesson_text.lower().strip() == "user safety: safe":
                    lesson_text = (
                        f"### 🧙‍♂️ Lesson Workspace: {lesson_title}\n\n"
                        f"Welcome to your lessons study guide for **{lesson_title}**! Mwalimu is pulling "
                        f"the standard curriculum framework notes directly from your KICD index. "
                        f"Review the sub-topics on your right, ask your AI teacher for guidance points, "
                        f"and hit the quiz challenge button below to advance your learning track velocity! 🚀"
                    )
                
                st.session_state[lesson_cache_key] = lesson_text
            except Exception as e:
                st.session_state[lesson_cache_key] = f"Could not load lesson contents. Details: {e}"

    st.markdown(st.session_state[lesson_cache_key])

    st.write("---")

    # =====================================================================
    # 💬 STEP 3: FULL-WIDTH CHAT WITH MWALIMU SECTION
    # =====================================================================
        # =====================================================================
    # STEP 3: FULL-WIDTH CHAT WITH MWALIMU SECTION
    # =====================================================================
    st.write("### Chat with Mwalimu")
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
            # STUDENT BUBBLE CONTAINER
            st.markdown(f"""
<div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 20px; width: 100%;">
<div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
<div style="text-align: left;">{msg["content"]}</div>
</div>
<div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">👤</div>
</div>
""", unsafe_allow_html=True)
        else:
            current_ai_index += 1
            id_tag = f"lesson_msg_{current_ai_index}"
            # MWALIMU AI CONTAINER
            st.markdown(f"""
<div id="{id_tag}" style="display: flex; justify-content: flex-start; align-items: center; gap: 10px; margin-bottom: 12px; width: 100%; scroll-margin-top: 80px;">
<div style="width: 32px; height: 32px; background-color: #FF4B4B; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">🧙‍♂️</div>
<div style="font-family: sans-serif; font-size: 13px; font-weight: 600; color: #FF4B4B; text-transform: uppercase; letter-spacing: 0.5px;">Mwalimu AI</div>
</div>
""", unsafe_allow_html=True)
            st.markdown(msg["content"])
            st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

    # SCROLL ENGINE AUTOMATION MANAGER
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
        
    st.markdown("<div style='margin-bottom: 100px;'></div>", unsafe_allow_html=True)

    # =====================================================================
    # STEP 4: GLOBAL CHAT INPUT WINDOW LOCKED AT THE BOTTOM OF THE PAGE
    # =====================================================================
        # =====================================================================
    # STEP 4: GLOBAL CHAT INPUT WINDOW LOCKED AT THE BOTTOM OF THE PAGE
    # =====================================================================
    if user_query := st.chat_input("Ask a question about this lesson...", key=f"input_{lesson_id}"):
        # 1. Append user query to history tracking array memory records immediately
        st.session_state[lesson_chat_history_key].append({"role": "user", "content": user_query})
        
        # 🌟 FIXED: Instantly render the student bubble on screen before any API logic runs
        st.markdown(f"""
<div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 20px; width: 100%;">
<div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
<div style="text-align: left;">{user_query}</div>
</div>
<div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">👤</div>
</div>
""", unsafe_allow_html=True)

        chat_profile = {**student_profile, "subject": subject, "topic": lesson_title, "sub_topic": lesson_title}
        adaptive_notes = f"This conversation is locked directly to helping the student understand the following lesson content block: {st.session_state[lesson_cache_key][:400]}"
        
        current_ai_count = sum(1 for m in st.session_state[lesson_chat_history_key] if m["role"] not in ["student", "user"]) + 1
        next_scroll_target_id = f"msg_lms_{current_ai_count}"
        
        # 2. Render the upcoming Mwalimu avatar placeholder row
        st.markdown(f"""
<div id="{next_scroll_target_id}" style="display: flex; justify-content: flex-start; align-items: center; gap: 10px; margin-bottom: 12px; width: 100%; scroll-margin-top: 80px;">
<div style="width: 32px; height: 32px; background-color: #FF4B4B; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);"></div>
<div style="font-family: sans-serif; font-size: 13px; font-weight: 600; color: #FF4B4B; text-transform: uppercase; letter-spacing: 0.5px;">Mwalimu AI</div>
</div>
""", unsafe_allow_html=True)
        
        assistant_placeholder = st.empty()
        
        response_stream = ask_mwalimu(
            question=user_query,
            student=chat_profile,
            messages=st.session_state[lesson_chat_history_key][:-1],
            adaptive_context=adaptive_notes
        )
        
        # ==================================================== 
        # CHUNK STREAMING EVALUATION LOOP
        # ====================================================
        assistant_text = ""
        try:
            for chunk in response_stream:
                if isinstance(chunk, str):
                    if "error" in chunk.lower() or "injected" in chunk.lower():
                        continue
                    assistant_text += chunk
                    assistant_placeholder.markdown(assistant_text)
                    continue
                    
                if hasattr(chunk, 'choices') and chunk.choices:
                    try:
                        choice_item = chunk.choices[0]
                        if hasattr(choice_item, 'delta') and choice_item.delta:
                            delta_content = getattr(choice_item.delta, 'content', None)
                            if delta_content is not None:
                                if '"error":' in str(delta_content) or 'openai-error' in str(delta_content).lower():
                                    continue
                                assistant_text += str(delta_content)
                                assistant_placeholder.markdown(assistant_text)
                    except (IndexError, AttributeError, KeyError):
                        continue
        except Exception as stream_err:
            print(f"[LMS Chat Stream Warning] Connection stream interrupted: {stream_err}")
            
        if not assistant_text:
            assistant_text = "Mwalimu encountered a brief connection stutter. Please try sending your query again!"
            assistant_placeholder.markdown(assistant_text)
            
        # 3. Save to history and refresh the page to lock both blocks inside your structural tracking loop
        st.session_state[lesson_chat_history_key].append({"role": "assistant", "content": assistant_text})
        st.rerun()
