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
    # Display previous chat messages (State-Guarded Scroll Tracker)
    # -----------------------------
    grade = st.session_state.get("grade", "")  
    assistant_messages_count = sum(1 for m in st.session_state.ask_mwalimu_history if m["role"] not in ["student", "user"])
    current_ai_index = 0

    for msg in st.session_state.ask_mwalimu_history:
# ADD THIS LINE TO SKIP VOICE MESSAGES:
        if msg.get("is_voice") == 1:
            continue
            
        if msg["role"] in ["student", "user"]:
            # 👤 STUDENT CONTAINER
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
            
            if "image_preview" in msg and msg["image_preview"]:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="max-width: 320px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.15); border: 1px solid #424656;">
                        <img src="{msg["image_preview"]}" style="width: 100%; display: block;" />
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if "file_preview" in msg and msg["file_preview"]:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="background-color: #2F3037; color: #ECECF1; padding: 10px 14px; border-radius: 12px; border: 1px solid #424656; display: flex; align-items: center; gap: 8px; font-size: 13px; font-family: sans-serif;">
                        📄 {msg["file_preview"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        else:
            current_ai_index += 1
            # Create anchor tags directly matching your document strategy
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
            
            st.markdown(msg["content"])
            st.markdown("<div style='margin-bottom: 32px;'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # 🛠️ SCROLL ENGINE AUTOMATION MANAGER (DOCUMENT METHOD)
    # ----------------------------------------------------
    # Target the absolute newest assistant message ID block
    target_scroll_id = f"msg_{assistant_messages_count}"

    # ONLY execute scroll action once when the flag is raised!
    if st.session_state.new_message and assistant_messages_count > 0:
        st.session_state.new_message = False  # 👈 DEACTIVATE IMMEDIATELY TO FREE UP SCROLLING
        
        # Inject modern compliant production HTML script snippet
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
    # State-Driven Upgrade Gatekeeper Banner
    # ----------------------------------------------------
    if st.session_state.get("chat_limit_reached"):
        st.error("⚠️ Daily question Limit Reached, Wait for 24hrs or Upgrade to Premium to continue!")
        
        if st.button("🚀 Upgrade to Premium", key="chat_upgrade_unique_btn"):
            # 1. Clear the banner state flag immediately 
            st.session_state.pop("chat_limit_reached", None)
            
            # 2. Stage a temporary trigger instead of a permanent True state
            st.session_state.trigger_chat_upgrade_modal = True
            st.rerun()

    # ----------------------------------------------------
    # Safe Modal Activation Layer (Prevents Continuous Loops)
    # ----------------------------------------------------
    if st.session_state.get("trigger_chat_upgrade_modal"):
        # Instantly remove the flag so it only runs EXACTLY once
        st.session_state.pop("trigger_chat_upgrade_modal", None)
        upgrade_modal()

    # ----------------------------------------------------
    # Chat Input
    # ----------------------------------------------------        
    chat_payload = st.chat_input(
        "Ask Mwalimu anything...",
        accept_file=True,
        file_type=["pdf", "png", "jpg", "jpeg"]
    )

    if chat_payload:
        # 1. Extract text and uploaded files from payload safely
        user_question = str(chat_payload.text) if hasattr(chat_payload, "text") else str(chat_payload)
        
        uploaded_file = None
        if hasattr(chat_payload, "files") and chat_payload.files:
            uploaded_file = chat_payload.files
        conversation_subject = st.session_state.get(
            "active_subject",
            "General Studies"
        )

        # 2. Retrieve student metadata details for subscription verification
        student_profile = get_student_data(st.session_state.user_email)
        subscription = student_profile.get("subscription", {}) if student_profile else {}
        tier = subscription.get("tier", "Free")
        uid = st.session_state.get("uid") or st.session_state.user_email
        
        #  FIXED CODE:
        if not st.session_state.get("student_name"):

            st.warning("Please create Student Profile in the sidebar first!")
        elif not verify_tier_allowance(uid, tier, "questions"):
            st.session_state.chat_limit_reached = True
            st.rerun()
        else:
            st.session_state.pop("chat_limit_reached", None)
            ai_student_context = st.session_state.get("active_student_profile", {
                "student_name": st.session_state.get("student_name", "Student"),
                "name": st.session_state.get("student_name", "Student"),
                "grade": st.session_state.get("grade", "Grade 6"),
                "age": int(st.session_state.get("age", 12)) if st.session_state.get("age") else 12,
                "preferred_language": st.session_state.get("language", "English"),
                "subject": conversation_subject,
                "topic": "",
                "sub_topic": "",
                "learning_outcome": ""
            })
            # 3. 🔒 PREMIUM TIER FILE ATTACHMENT GUARD LOCK
            attachment_payload = None
            if uploaded_file:
                # 💡 CHANGED: Checks if user has remaining upload limits instead of blocking free users outright
                if not verify_tier_allowance(uid, tier, "has_upload"):
                    st.error("🔒 **Mwalimu Document Scanner Upload Today Limit Reached.** Upgrade to Premium to get Unlimited Upload!")
                    if st.button("🚀 Upgrade to Premium Now", key="upload_guard_upgrade_btn"):
                        st.session_state.trigger_chat_upgrade_modal = True
                        st.rerun()
                    st.stop()
                if st.session_state.get("trigger_chat_upgrade_modal"):
                    # Instantly remove the flag so it only runs EXACTLY once
                    st.session_state.pop("trigger_chat_upgrade_modal", None)
                    upgrade_modal()
                else:
                    attachment_payload = MwalimuVisionService.process_chat_input_file(uploaded_file)
            
            # 4. Build message payload dictionary and append to state history
            user_message_block = {"role": "student", "content": user_question}
            if attachment_payload:
                if attachment_payload.get("type") == "image_base64":
                    user_message_block["image_preview"] = attachment_payload["content"]
                elif attachment_payload.get("type") == "text_extraction":
                    user_message_block["file_preview"] = attachment_payload["filename"]
            conversation_subject = st.session_state.get(
                                "active_subject",
                                "General Studies"
                            )
            # Append user text to memory history instantly
            st.session_state.ask_mwalimu_history.append(user_message_block)

            # FIX: Pass the file attachment dictionary payload so it's written into SQLite
                    # 1. Extract and sanitize the string values outside the function parameters block
            age_raw = str(st.session_state.get("age", ""))
            safe_age = int(age_raw) if age_raw.isdigit() else 12

            # 2. Call your database save engine function cleanly
            save_ask_mwalimu_message(
                student_uid=str(st.session_state.get("uid", "")),
                student_name=str(st.session_state.get("student_name", "Student")),
                grade=grade,
                age=safe_age,
                subject=conversation_subject,
                role="user",
                message=user_question,
                attachment=attachment_payload
            )


            st.session_state.ask_mwalimu_history = get_ask_mwalimu_history(
                str(st.session_state.get("uid", "")),
                conversation_subject
            )
                                # 5. IMMEDIATELY DISPLAY USER BUBBLE ON SCREEN (No waiting!)
            # This mirrors your Page 42 custom avatar design look instantly
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; align-items: flex-start; gap: 10px; margin-bottom: 20px; width: 100%;">
                <div style="background-color: #2F3037; color: #ECECF1; padding: 12px 18px; border-radius: 20px; max-width: 70%; font-family: sans-serif; font-size: 15px; line-height: 1.6;">
                    <div style="text-align: left;">{user_question}</div>
                </div>
                <div style="width: 32px; height: 32px; background-color: #40414F; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 15px; flex-shrink: 0;">
                    👤
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if attachment_payload and attachment_payload.get("type") == "image_base64":
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 20px; width: 100%; padding-right: 42px; box-sizing: border-box;">
                    <div style="max-width: 320px; border-radius: 12px; overflow: hidden; border: 1px solid #424656;">
                        <img src="{attachment_payload["content"]}" style="width: 100%; display: block;" />
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 6. TRIGGER INSTANT SCROLL SNAPPING DOWNWARD BEFORE STREAMING
            # Calculate index position token target tags dynamically
            current_ai_count = sum(1 for m in st.session_state.ask_mwalimu_history if m["role"] not in ["student", "user"]) + 1
            next_scroll_target_id = f"msg_{current_ai_count}"
            
            st.markdown(f'<div id="chat-page-tail" style="height: 5px;"></div>', unsafe_allow_html=True)
            st.html("""
                <script>
                    window.parent.document.getElementById('chat-page-tail').scrollIntoView({behavior: 'smooth', block: 'end'});
                </script>
            """)

            # 7. CREATE EMPTY ASSISTANT CHAT CONTAINER BUBBLE ROW
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
            
            # Dedicated Streamlit placeholder layer window block
            assistant_placeholder = st.empty()
                    # 🚀 ADD THIS TO REBUILD THE EXPECTED DICTIONARY PAYLOAD:
                    # 🚀 FIX: Change "name" to "student_name" so services/ai.py can parse it
            student_profile_payload = {
                "student_name": st.session_state.get("student_name", "Student"), # 👈 UPDATED KEY
                "grade": st.session_state.get("grade", "Grade 6"),
                "age": int(st.session_state.get("age", 12)) if st.session_state.get("age") else 12,
                "preferred_language": st.session_state.get("language", "English"),
                "subject": st.session_state.get("active_subject", "Science and Technology"),
                "topic": st.session_state.get("active_topic", ""),
                "sub_topic": st.session_state.get("active_sub_topic", ""),
                "learning_outcome": st.session_state.get("active_learning_outcome", "")
            }

            
            # 7. TRIGGER GENERATOR INSTANTLY WITH A CHATGPT LOADING WAVE
            # ====================================================
            # Create an explicit temporary layout box for the custom animation
                # ====================================================
            # 7. TRIGGER GENERATOR INSTANTLY WITH A NATIVE CHATGPT LOADER
            # ====================================================
            # 🎯 FIX: Using a clean, immediate text block that forces Streamlit to render instantly
                # ====================================================
            # 7. TRIGGER GENERATOR INSTANTLY WITH AN UNBLOCKABLE SVG ANIMATED LOADER
            # ====================================================
            # 🎯 FIX: Using inline SVG animations allows the browser to render moving dots instantly
            # while the Python engine is busy establishing the network connection stream.
            loader_placeholder = st.empty()
            loader_placeholder.markdown(
                """
                <div style="display: flex; align-items: center; gap: 10px; padding: 12px 0; margin-bottom: 5px;">
                    <span style="font-size: 16px; color: var(--text-color); opacity: 0.65; font-style: italic;">
                        💭 Mwalimu is thinking
                    </span>
                    <svg width="35" height="12" viewBox="0 0 60 20" style="vertical-align: middle;">
                        <circle cx="10" cy="10" r="7" fill="var(--text-color)">
                            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.2s" repeatCount="indefinite" begin="0s"/>
                        </circle>
                        <circle cx="30" cy="10" r="7" fill="var(--text-color)">
                            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.2s" repeatCount="indefinite" begin="0.2s"/>
                        </circle>
                        <circle cx="50" cy="10" r="7" fill="var(--text-color)">
                            <animate attributeName="opacity" values="0.2;1;0.2" dur="1.2s" repeatCount="indefinite" begin="0.4s"/>
                        </circle>
                    </svg>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Invoke your backend streaming connection gateway
            response_stream = ask_mwalimu(
                question=user_question,
                student=ai_student_context,
                messages=st.session_state.ask_mwalimu_history,
                attachment=attachment_payload
            )


            # ==================================================== 
            # 8. REASONING-AWARE CHATGPT STYLE STREAMING LOOP (TYPE-SAFE)
            # ====================================================
            assistant_text = ""
            thought_text = ""
            has_cleared_loader = False  # Track if the placeholder message has been wiped out

            # Clear individual element layout slots right below the loader space
            thought_container = st.empty()
            assistant_placeholder = st.empty()

            try:
                for chunk in response_stream:
                    # Type-safe dynamic property lookup to extract choices list
                    choices_list = getattr(chunk, "choices", None)
                    
                    if choices_list and len(choices_list) > 0:
                        try:
                            first_choice = choices_list[0]
                            delta = getattr(first_choice, "delta", None)
                            
                            if delta:
                                # A. Stream model thought process tokens live
                                reasoning = getattr(delta, "reasoning_content", None)
                                if reasoning:
                                    # Wipe out the loader text message instantly on the very first incoming data chunk
                                    if not has_cleared_loader:
                                        loader_placeholder.empty()
                                        has_cleared_loader = True

                                    thought_text += str(reasoning)
                                    with thought_container:
                                        with st.expander("💭 Mwalimu is thinking...", expanded=True):
                                            st.markdown(thought_text)
                                            
                                # B. Stream final educational conversational answers
                                content = getattr(delta, "content", None)
                                if content:
                                    # Wipe out the loader text message instantly if not already done
                                    if not has_cleared_loader:
                                        loader_placeholder.empty()
                                        has_cleared_loader = True

                                    # Automatically fold up the reasoning block when the final response prints
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
                        
                        # Wipe out loader for plain string tokens too
                        if not has_cleared_loader:
                            loader_placeholder.empty()
                            has_cleared_loader = True

                        assistant_text += chunk
                        assistant_placeholder.markdown(assistant_text)
                            
            except Exception as stream_err:
                print(f"[Mwalimu Stream Warning] Interrupted: {stream_err}")

            # Final sweep boundary cleanup: ensure loader gets wiped out once everything completes
            if not has_cleared_loader:
                loader_placeholder.empty()

            # Fallback error messaging block assignment
            if not assistant_text:
                assistant_text = "Mwalimu encountered a brief connection stutter. Please try sending your query again!"
                assistant_placeholder.markdown(assistant_text)







            
            # ====================================================================
            # 9. SAVE COMPLETE HISTORY RECORD DATA ONLY AFTER STREAMING COMPLETES
            # ====================================================================
            MwalimuDBService.increment_usage(uid, "questions")

            #  FIX: Check the structural attachment dictionary extracted on Page 7
            if attachment_payload is not None:
                MwalimuDBService.increment_usage(uid, "has_upload")

            st.session_state.ask_mwalimu_history.append({"role": "assistant", "content": assistant_text})
                        # 🌟 FIXED: Explicitly naming every argument fixes the Pylance parameter lookup error!
            save_ask_mwalimu_message(
                student_uid=str(st.session_state.get("uid", "")),
                student_name=str(st.session_state.get("student_name", "Student")),
                grade=grade,
                age=safe_age,
                subject=conversation_subject,
                role="assistant",
                message=assistant_text
            )

            st.session_state.ask_mwalimu_history = get_ask_mwalimu_history(
                str(st.session_state.get("uid", "")),
                conversation_subject
            )