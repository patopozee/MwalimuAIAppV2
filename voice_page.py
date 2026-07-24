import streamlit as st
import io
import json
import sqlite3
from gtts import gTTS  
from streamlit_mic_recorder import speech_to_text  
from services.ai import ask_mwalimu_voice  
from services.database import (
    save_voice_chat_message, 
    get_voice_chat_history, 
    clear_voice_chat_history_only
)

def render_voice_tutor_page(client):
    st.title("🎙️ Mwalimu AI - Voice Tutor")
    st.write("Click the microphone below to talk with your AI Teacher. Speak clearly!")

    # 1. State Management Setup
    if "voice_recorder_version" not in st.session_state:
        st.session_state.voice_recorder_version = 0
    if "voice_session_active" not in st.session_state:
        st.session_state.voice_session_active = False
    if "voice_chat_history" not in st.session_state:
        st.session_state.voice_chat_history = []
    if "voice_cache" not in st.session_state:
        st.session_state.voice_cache = {}

    # Gather Student Parameters Safely
    name = st.session_state.get("student_name", "Student")
    grade = st.session_state.get("grade", "Grade 6")
    age = st.session_state.get("age", 13)
    learning_style = st.session_state.get("learning_style", "Interactive")
    language = st.session_state.get("language", "English")
    
    subject = st.session_state.get("active_subject", "Mathematics")
    topic = st.session_state.get("active_topic", "Whole Numbers")
    sub_topic = st.session_state.get("active_sub_topic", "Place Value")
    learning_outcome = st.session_state.get("active_learning_outcome", "General Learning Outcome")

    # 🛡️ FIX 1: ISOLATE THE STUDENT DICTIONARY OBJECT NAME
    voice_student_profile = {
        "name": name, 
        "grade": grade, 
        "age": int(age),
        "subject": subject,    
        "topic": topic,        
        "sub_topic": sub_topic,
        "learning_style": learning_style, 
        "language": language
    }

    # 2. Database Fetch & Initial Normalization
    student_uid = str(st.session_state.get("uid", ""))
    current_subject = st.session_state.get("active_subject", "General Studies")

    if student_uid:

        if (
            st.session_state.get("last_voice_uid") != student_uid
            or
            st.session_state.get("last_voice_subject") != current_subject
        ):

            try:

                all_raw_history = get_voice_chat_history(
                    student_uid,
                    current_subject
                )

                st.session_state.voice_chat_history = []

                for msg in all_raw_history:

                    role_type = msg.get("role")

                    if role_type in ["voice_user", "voice_student", "user"]:
                        msg["role"] = "user"

                    elif role_type in ["voice_assistant", "assistant"]:
                        msg["role"] = "assistant"

                    st.session_state.voice_chat_history.append(msg)

                st.session_state.last_voice_uid = student_uid
                st.session_state.last_voice_subject = current_subject

            except Exception:
                st.session_state.voice_chat_history = []

    # 3. Message Render Loop (Includes File / Image Attachments Previewer)
    for msg in st.session_state.voice_chat_history:
        if msg["role"] == "user":
            st.info(f"🗣️ **Mwanafunzi ({name}):** {msg['content']}")
            if msg.get("audio_bytes"):
                st.audio(msg["audio_bytes"], format="audio/wav")
            # If the text message row contains an associated media payload, show it
            if msg.get("image_preview"):
                st.image(msg["image_preview"], caption="Uploaded Workspace Screenshot", width=350)
                
        elif msg["role"] == "assistant":
            st.success(f"🧙‍♂️ **Mwalimu:** {msg['content']}")
            msg_content = msg['content']
            cached_audio = st.session_state.voice_cache.get(msg_content) or msg.get("audio_bytes")
            if cached_audio:
                st.audio(cached_audio, format="audio/mp3")

    live_response_container = st.container()
    st.write("---") 

    # 4. Voice Input Microphones Stream Processing Context
    target_stt_lang = "sw" if "swahili" in str(language).lower() else "en"
    transcribed_text = speech_to_text(
        start_prompt="🎙️ Click & Start Speaking",
        stop_prompt="🛑 Stop & Send Voice Note",
        language=target_stt_lang,
        key=f"voice_stt_v_{st.session_state.voice_recorder_version}"  
    )

    if transcribed_text and not st.session_state.voice_session_active:
        st.session_state.voice_session_active = True
        transcribed_text = str(transcribed_text).strip()
        
        # Cleanup unwanted smart assistant phrasing triggers
        transcribed_text = transcribed_text.replace("play music by", "")
        transcribed_text = transcribed_text.replace("play music", "")
        transcribed_text = transcribed_text.strip()
        
        if transcribed_text:
            # 🛡️ FIX 2: ISOLATE THE TIMELINE REPLICATOR VARIABLE NAME
            voice_history_payload = list(st.session_state.voice_chat_history)
            
            user_msg_dict = {"role": "user", "content": transcribed_text, "is_voice": True, "audio_bytes": None}
            st.session_state.voice_chat_history.append(user_msg_dict)

            with live_response_container:
                st.info(f"🗣️ **Mwanafunzi ({name}):** {transcribed_text}")
                st.write("") 
                st.markdown("🧙‍♂️ **Mwalimu AI is typing...**")
                assistant_placeholder = st.empty()
            
            # Save User Input Message EXACTLY Once
            save_voice_chat_message(
                student_uid=student_uid,
                student_name=name,
                grade=grade,
                age=int(age),
                subject=st.session_state.get(
                    "active_subject",
                    "General Studies"
                ),
                role="user",
                message=transcribed_text,
                audio_bytes=None
            )

            try:
                adaptive_context = f"Voice Session. Subject: {subject}, Topic: {topic}"
                
                # 🛡️ FIX 3: PASS THE ENTIRELY ISOLATED POINTER FIELDS DOWN
                response_stream = ask_mwalimu_voice(
                    question=transcribed_text,
                    student=voice_student_profile,
                    messages=st.session_state.voice_chat_history,
                    adaptive_context=adaptive_context
                )

                ai_response_text = ""
                for chunk in response_stream:
                    if isinstance(chunk, str):
                        if not any(token in chunk for token in ["We need to", "Current context:", "Let's count:", "Under 50"]):
                            ai_response_text += chunk
                            assistant_placeholder.markdown(ai_response_text)
                        continue

                    if hasattr(chunk, 'choices') and chunk.choices:
                        try:
                            choice_item = chunk.choices[0]
                            if hasattr(choice_item, 'delta') and choice_item.delta:
                                delta_content = getattr(choice_item.delta, 'content', None)
                                if delta_content is not None:
                                    delta_str = str(delta_content)
                                    if "We need to" in delta_str or "Current context" in delta_str:
                                        continue
                                    ai_response_text += delta_str
                                    assistant_placeholder.markdown(ai_response_text)
                        except (IndexError, AttributeError, KeyError):
                            continue

                if ai_response_text and ai_response_text.strip():
                    ai_response_text = ai_response_text.replace("User Safety: safe", "").strip()
                    
                    with live_response_container:
                        with st.spinner("🔊 Generating Mwalimu's voice file..."):
                            try:
                                speak_lang = "sw" if "swahili" in str(language).lower() else "en"
                                tts_live = gTTS(text=ai_response_text, lang=speak_lang, slow=False)
                                live_audio_fp = io.BytesIO()
                                tts_live.write_to_fp(live_audio_fp)
                                
                                audio_bytes = live_audio_fp.getvalue()
                                st.session_state.voice_cache[ai_response_text] = audio_bytes
                                
                                # Save AI response message EXACTLY once with generated speech binary
                                save_voice_chat_message(
                                    student_uid=student_uid,
                                    student_name=name,
                                    grade=grade,
                                    age=int(age),
                                    subject=st.session_state.get(
                                        "active_subject",
                                        "General Studies"
                                    ),
                                    role="assistant",
                                    message=ai_response_text,
                                    audio_bytes=audio_bytes
                                )
                                
                                # Sync update to memory state model array
                                st.session_state.voice_chat_history.append({
                                    "role": "assistant", 
                                    "content": ai_response_text,
                                    "is_voice": True,
                                    "audio_bytes": audio_bytes
                                })
                                
                                # Play out aloud instantly on browser layer
                                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                            except Exception as audio_err:
                                print(f"gTTS network generation latency: {audio_err}")

            except Exception as e:
                st.error(f"Mwalimu setup issue: {str(e)}")

            # 🏎️ Page Re-initialization Optimization
            st.session_state.voice_recorder_version += 1
            st.session_state.voice_session_active = False
            st.rerun()

  
    # --- DEDICATED CONFIRMATION DIALOG MODAL ---
    @st.dialog("⚠️ Clear Voice Data")
    def confirm_clear_voice_dialog():
        current_subject = st.session_state.get(
            "active_subject",
            "General Studies"
        )

        st.warning(
            f"You are about to permanently delete all Voice Tutor conversations for **{current_subject}**.\n\n"
            "Voice conversations from other subjects will remain available.\n\n"
            "This action cannot be undone."
        )
        
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if st.button(
                    "Yes, Clear This Subject history",
                    use_container_width=True,
                    type="primary"
                ):
                # 1. Clean the backend database rows
                clear_voice_chat_history_only(student_uid=str(st.session_state.get("uid", "")),
                    grade=st.session_state.get("grade", "Grade 6"),
                    age=int(st.session_state.get("age", 12)),
                    subject=st.session_state.get(
                        "active_subject",
                        "General Studies"))
                
                # 2. Reset visual RAM session storage arrays
                st.session_state.voice_chat_history = []
                st.session_state.voice_cache = {}
                st.session_state.voice_session_active = False

                from services.database import get_voice_chat_history
                if hasattr(get_voice_chat_history, "clear"):
                    get_voice_chat_history.clear()

                # 3. Change component key to reset widget state smoothly
                st.session_state.voice_recorder_version += 1
                
                st.toast("Voice database history records removed completely!")
                st.rerun()
                
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

    # 5. Cleaned Single Action Button Trigger Panel
    if len(st.session_state.voice_chat_history) > 0:
        st.write("") 
        
        # Kept only the permanent deletion button as requested
        if st.button("🗑️ Permanently Delete Voice DB Logs", use_container_width=True):
            confirm_clear_voice_dialog()