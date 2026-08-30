import streamlit as st
from services.tier_guard import verify_tier_allowance
from services.ai import ask_mwalimu
from services.vision_service import MwalimuVisionService
from services.db_service import MwalimuDBService
from services.upgrade_modal import upgrade_modal

from services.database import (
    get_ask_mwalimu_history,
    save_ask_mwalimu_message,
    get_student_data
)

def render(): 
    # Context Variable Pre-fetching
    uid = st.session_state.get("uid") or st.session_state.get("user_email", "")
    grade = st.session_state.get("grade", "Grade 6")
    conversation_subject = st.session_state.get("active_subject", "General Studies")
    
    if "ask_mwalimu_history" not in st.session_state:
        st.session_state.ask_mwalimu_history = []

    if "new_message" not in st.session_state:
        st.session_state.new_message = False

    st.markdown("""
        <div style="
            background-color: #101726; 
            border: 1px solid rgba(36, 115, 242, 0.15); 
            border-radius: 14px; 
            padding: 20px; 
            margin-bottom: 25px;
        ">
            <h3 style="margin-top: 0; color: #FFFFFF; font-size: 1.3rem; margin-bottom: 8px;">
                👋 Welcome to Mwalimu AI – Your Adaptive Learning Partner
            </h3>
            <p style="color: #94A3B8; font-size: 14px; line-height: 1.5; margin-bottom: 15px;">
                Start by setting up your student profile in the sidebar. Explore your interactive learning hubs below:
            </p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
                <div style="color: #E2E8F0; font-size: 13.5px;">💬 <b>Main Chat & Voice:</b> Ask questions or talk to a live voice tutor.</div>
                <div style="color: #E2E8F0; font-size: 13.5px;">⚡ <b>AI Generators:</b> Create custom study flashcards and revisions.</div>
                <div style="color: #E2E8F0; font-size: 13.5px;">🏫 <b>LMS Dashboard:</b> Complete structured lessons to earn certificates.</div>
                <div style="color: #E2E8F0; font-size: 13.5px;">🏆 <b>Leaderboard:</b> Challenge yourself with quizzes and rank nationally.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # =====================================================
    # CHAT WITH MWALIMU SECTION
    # =====================================================
    st.markdown("---")
    st.write("### 💬 Chat with Mwalimu")

    # Display previous chat messages
    assistant_messages_count = sum(1 for m in st.session_state.ask_mwalimu_history if m.get("role") not in ["student", "user"])
    current_ai_index = 0

    for msg in st.session_state.ask_mwalimu_history:
        # Skip voice-only records if specified
        if msg.get("is_voice") == 1:
            continue
            
        if msg.get("role") in ["student", "user"]:
            # 👤 STUDENT CONTAINER
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 10px; width: 100%;">
                <div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="text-align: left;">{msg.get("content", "")}</div>
                </div>
                <div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    👤
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            img_src = msg.get("image_preview") or msg.get("preview")
            if img_src:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="max-width: 320px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border: 1px solid #424656;">
                        <img src="{img_src}" style="width: 100%; display: block;" />
                    </div>
                </div>
                """, unsafe_allow_html=True)

            file_src = msg.get("file_preview")
            if file_src:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="background-color: #2F3037; color: #ECECF1; padding: 10px 14px; border-radius: 12px; border: 1px solid #424656; display: flex; align-items: center; gap: 8px; font-size: 13px; font-family: sans-serif;">
                        📄 {file_src}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        else:
            current_ai_index += 1
            id_tag = f"msg_{current_ai_index}"

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
            
            st.markdown(msg.get("content", ""))
            st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # 🛠️ SCROLL ENGINE AUTOMATION MANAGER
    # ----------------------------------------------------
    target_scroll_id = f"msg_{assistant_messages_count}"

    if st.session_state.new_message and assistant_messages_count > 0:
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

    # ----------------------------------------------------
    # State-Driven Upgrade Gatekeeper Banners
    # ----------------------------------------------------
    if st.session_state.get("chat_limit_reached"):
        st.error("⚠️ Daily question Limit Reached, Wait for 24hrs or Upgrade to Premium to continue!")
        if st.button("🚀 Upgrade to Premium", key="chat_upgrade_unique_btn"):
            st.session_state.pop("chat_limit_reached", None)
            st.session_state.trigger_chat_upgrade_modal = True
            st.rerun()

    if st.session_state.get("upload_limit_reached"):
        st.error("🔒 **Mwalimu Document Scanner Upload Today Limit Reached.** Upgrade to Premium to get Unlimited Upload!")
        if st.button("🚀 Upgrade to Premium Now", key="upload_guard_upgrade_btn"):
            st.session_state.pop("upload_limit_reached", None)
            st.session_state.trigger_chat_upgrade_modal = True
            st.rerun()

    if st.session_state.get("trigger_chat_upgrade_modal"):
        st.session_state.pop("trigger_chat_upgrade_modal", None)
        upgrade_modal()

    # ----------------------------------------------------
    # Chat Input Block
    # ----------------------------------------------------        
    chat_payload = st.chat_input(
        "Ask Mwalimu anything...",
        accept_file=True,
        file_type=["pdf", "png", "jpg", "jpeg"]
    )

    # =====================================================
    # LIVE MESSAGE SUBMISSION & STREAMING HANDLER
    # =====================================================
    if chat_payload:
        # 1. Extract message text & attachment files
        if hasattr(chat_payload, "text"):
            user_question = chat_payload.text or ""
        elif isinstance(chat_payload, dict):
            user_question = chat_payload.get("text", "")
        else:
            user_question = ""

        uploaded_file = None
        if hasattr(chat_payload, "files") and chat_payload.files:
            uploaded_file = chat_payload.files
        elif isinstance(chat_payload, dict) and "files" in chat_payload:
            uploaded_file = chat_payload["files"]

        # 2. Retrieve student metadata details
        user_email = st.session_state.get("user_email", "")
        student_profile = get_student_data(user_email) if user_email else {}
        subscription = student_profile.get("subscription", {}) if student_profile else {}
        tier = subscription.get("tier", "Free")

        # 3. Perform tier verification guard checks
        if not st.session_state.get("student_name"):
            st.warning("Please create Student Profile in the sidebar first!")
        elif not verify_tier_allowance(uid, tier, "questions"):
            st.session_state.chat_limit_reached = True
            st.rerun()
        else:
            st.session_state.pop("chat_limit_reached", None)
            
            ai_student_context = {
                "student_name": st.session_state.get("student_name", "Student"),
                "grade": grade,
                "age": int(st.session_state.get("age", 12)) if str(st.session_state.get("age", "")).isdigit() else 12,
                "preferred_language": st.session_state.get("language", "English"),
                "subject": conversation_subject,
                "topic": st.session_state.get("active_topic", ""),
                "sub_topic": st.session_state.get("active_sub_topic", ""),
                "learning_outcome": st.session_state.get("active_learning_outcome", "")
            }

            # 4. Handle attachments & standardize preview fields
            attachment_payload = None
            image_preview_url = None
            file_preview_name = None

            if uploaded_file:
                if not verify_tier_allowance(uid, tier, "has_upload"):
                    st.session_state.upload_limit_reached = True
                    st.rerun()
                else:
                    st.session_state.pop("upload_limit_reached", None)
                    attachment_payload = MwalimuVisionService.process_chat_input_file(uploaded_file)
                    
                    # Standardize extraction of image/file preview values
                    if attachment_payload:
                        image_preview_url = (
                            attachment_payload.get("preview") or 
                            attachment_payload.get("image_preview") or 
                            (attachment_payload.get("content") if attachment_payload.get("type") == "image_base64" else None)
                        )
                        file_preview_name = (
                            attachment_payload.get("file_preview") or 
                            attachment_payload.get("filename")
                        )

            # 5. Save incoming user message to memory & database
            age_raw = str(st.session_state.get("age", ""))
            safe_age = int(age_raw) if age_raw.isdigit() else 12

            save_ask_mwalimu_message(
                student_uid=str(uid),
                student_name=str(st.session_state.get("student_name", "Student")),
                grade=grade,
                age=safe_age,
                subject=conversation_subject,
                role="user",
                message=user_question,
                attachment=attachment_payload
            )

            # Append to session state for current turn
            st.session_state.ask_mwalimu_history.append({
                "role": "user",
                "content": user_question,
                "image_preview": image_preview_url,
                "file_preview": file_preview_name
            })

            # -------------------------------------------------
            # EXPLICITLY RENDER USER PROMPT + UPLOAD IMMEDIATELY
            # -------------------------------------------------
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 10px; width: 100%;">
                <div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                    <div style="text-align: left;">{user_question}</div>
                </div>
                <div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    👤
                </div>
            </div>
            """, unsafe_allow_html=True)

            if image_preview_url:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="max-width: 320px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border: 1px solid #424656;">
                        <img src="{image_preview_url}" style="width: 100%; display: block;" />
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if file_preview_name and not image_preview_url:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="background-color: #2F3037; color: #ECECF1; padding: 10px 14px; border-radius: 12px; border: 1px solid #424656; display: flex; align-items: center; gap: 8px; font-size: 13px; font-family: sans-serif;">
                        📄 {file_preview_name}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Auto-scroll focus to tail
            st.markdown(f'<div id="chat-page-tail" style="height: 5px;"></div>', unsafe_allow_html=True)
            st.html("""
                <script>
                    window.parent.document.getElementById('chat-page-tail').scrollIntoView({behavior: 'smooth', block: 'end'});
                </script>
            """)

            # 6. Stream View Node for Mwalimu AI
            next_scroll_target_id = f"msg_{assistant_messages_count + 1}"
            st.markdown(f"""
            <div id="{next_scroll_target_id}" style="display: flex; justify-content: flex-start; align-items: center; gap: 10px; margin-bottom: 12px; width: 100%; scroll-margin-top: 80px;">
                <div style="width: 32px; height: 32px; background-color: #FF4B4B; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                    👨‍🏫
                </div>
                <div style="font-family: sans-serif; font-size: 13px; font-weight: 600; color: #FF4B4B; text-transform: uppercase; letter-spacing: 0.5px;">
                    Mwalimu AI
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            loader_placeholder = st.empty()
            loader_placeholder.markdown(
                """
                <style>
                @keyframes cgpt-bounce {
                    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; } 
                    40% { transform: scale(1.0); opacity: 1; }
                }
                .cgpt-dots-wrapper {
                    display: flex; align-items: center; gap: 6px; padding: 8px 0; margin-bottom: 12px;
                }
                .cgpt-dots-wrapper span {
                    width: 8px; height: 8px; background-color: #ECECF1; border-radius: 50%; display: inline-block;
                    animation: cgpt-bounce 1.4s infinite ease-in-out both;
                }
                .cgpt-dots-wrapper span:nth-child(1) { animation-delay: -0.32s; }
                .cgpt-dots-wrapper span:nth-child(2) { animation-delay: -0.16s; }
                </style>
                <div class="cgpt-dots-wrapper">
                    <span></span><span></span><span></span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Invoke LLM Gateway Stream
            response_stream = ask_mwalimu(
                question=user_question,
                student=ai_student_context,
                messages=st.session_state.ask_mwalimu_history,
                attachment=attachment_payload
            )

            # 7. Type-Safe Stream Processing Loop
            assistant_text = ""
            thought_text = ""
            has_cleared_loader = False

            thought_container = st.empty()
            assistant_placeholder = st.empty()

            try:
                for chunk in response_stream:
                    choices_list = getattr(chunk, "choices", None)
                    
                    if choices_list and len(choices_list) > 0:
                        try:
                            first_choice = choices_list[0]
                            delta = getattr(first_choice, "delta", None)
                            
                            if delta:
                                reasoning = getattr(delta, "reasoning_content", None)
                                if reasoning:
                                    if not has_cleared_loader:
                                        loader_placeholder.empty()
                                        has_cleared_loader = True

                                    thought_text += str(reasoning)
                                    with thought_container:
                                        with st.expander("💭 Mwalimu is thinking...", expanded=True):
                                            st.markdown(thought_text)
                                            
                                content = getattr(delta, "content", None)
                                if content:
                                    if not has_cleared_loader:
                                        loader_placeholder.empty()
                                        has_cleared_loader = True

                                    if thought_text:
                                        with thought_container:
                                            with st.expander("💭 Thought Process Complete", expanded=False):
                                                st.markdown(thought_text)
                                                
                                    assistant_text += str(content)
                                    assistant_placeholder.markdown(assistant_text)
                        except (IndexError, AttributeError, TypeError):
                            pass
                            
                    elif isinstance(chunk, str):
                        if "error" in chunk.lower() or "injected" in chunk.lower():
                            continue
                        
                        if not has_cleared_loader:
                            loader_placeholder.empty()
                            has_cleared_loader = True

                        assistant_text += chunk
                        assistant_placeholder.markdown(assistant_text)
                            
            except Exception as stream_err:
                print(f"[Mwalimu Stream Warning] Interrupted: {stream_err}")

            if not has_cleared_loader:
                loader_placeholder.empty()

            if not assistant_text:
                assistant_text = "Mwalimu encountered a brief connection stutter. Please try sending your query again!"
                assistant_placeholder.markdown(assistant_text)

            # 8. Persistence & Metrics Increment
            MwalimuDBService.increment_usage(uid, "questions")

            if attachment_payload is not None:
                MwalimuDBService.increment_usage(uid, "has_upload")

            save_ask_mwalimu_message(
                student_uid=str(uid),
                student_name=str(st.session_state.get("student_name", "Student")),
                grade=grade,
                age=safe_age,
                subject=conversation_subject,
                role="assistant",
                message=assistant_text
            )

            # Finalize sync and set scroll flags
            st.session_state.ask_mwalimu_history = get_ask_mwalimu_history(
                str(uid),
                conversation_subject
            )
            st.session_state.new_message = True
            st.rerun()