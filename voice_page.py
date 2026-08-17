#voice_page.py
import streamlit as st
import io
import os
import json
import sqlite3
import time
import asyncio
import edge_tts
import tempfile
import re
from streamlit_mic_recorder import speech_to_text
from services.ai import ask_mwalimu_voice
from services.database import (
    save_voice_chat_message,
    get_voice_chat_history,
    clear_voice_chat_history_only
)
from services.audio_duration import get_audio_duration


def generate_edge_tts_audio(text: str, voice: str) -> bytes:
    """Helper to run the async edge-tts generation loop and return bytes."""
    async def _async_gen():
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(temp_file.name)
            temp_path = temp_file.name

        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
        try:
            os.remove(temp_path)
        except:
            pass
        return audio_bytes

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(_async_gen())


def clean_math_transcript(text: str) -> str:

    corrections = {
        "to": "two",
        "too": "two",
        "for": "four",
        "ate": "eight",
        "won": "one",
        "tree": "three",
        "sex": "six",
        "free": "three",
        "owe": "zero",
        "oh": "zero",
    }

    words = text.lower().split()

    cleaned = [
        corrections.get(word, word)
        for word in words
    ]

    return " ".join(cleaned)


def render_voice_tutor_page(client):
    st.title("🎙️ Mwalimu AI - Voice Tutor")
    st.write("Click the microphone below to talk with your AI Teacher. Speak clearly!")

    # 1. State Machine Initialization
    if "voice_stage" not in st.session_state:
        st.session_state.voice_stage = "idle"  # Stages: idle, thinking, speaking
    if "voice_recorder_version" not in st.session_state:
        st.session_state.voice_recorder_version = 0
    if "voice_chat_history" not in st.session_state:
        st.session_state.voice_chat_history = []
    if "voice_cache" not in st.session_state:
        st.session_state.voice_cache = {}
    if "pending_user_text" not in st.session_state:
        st.session_state.pending_user_text = ""
    if "playback_end_time" not in st.session_state:
        st.session_state.playback_end_time = None

    # Gather Student Parameters Safely
    name = st.session_state.get("student_name", "Student")
    grade = st.session_state.get("grade", "Grade 6")
    age = st.session_state.get("age", 13)
    learning_style = st.session_state.get("learning_style", "Interactive")
    language = st.session_state.get("language", "English")

    subject = st.session_state.get("active_subject", "Mathematics")
    topic = st.session_state.get("active_topic", "Whole Numbers")
    sub_topic = st.session_state.get("active_sub_topic", "Place Value")

    voice_student_profile = {
        "name": name, "grade": grade, "age": int(age),
        "subject": subject, "topic": topic, "sub_topic": sub_topic,
        "learning_style": learning_style, "language": language
    }

    # 2. Handle Playback Timer Unlock (If Speaking)
    if st.session_state.voice_stage == "speaking" and st.session_state.playback_end_time:
        if time.time() >= st.session_state.playback_end_time:
            # Audio finished playing! Safely unlock back to idle
            st.session_state.voice_stage = "idle"
            st.session_state.playback_end_time = None
            st.session_state.voice_recorder_version += 1
            st.rerun()

    # 3. Database Sync & Initialization
    student_uid = str(st.session_state.get("uid", ""))
    current_subject = st.session_state.get("active_subject", "General Studies")

    if student_uid:
        if (st.session_state.get("last_voice_uid") != student_uid or
                st.session_state.get("last_voice_subject") != current_subject):
            try:
                all_raw_history = get_voice_chat_history(student_uid, current_subject)
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

    # =========================================================================
    # FIXED LAYOUT ANCHORS
    # -------------------------------------------------------------------------
    # These are declared ONCE, in a fixed order, before any conditional
    # rendering happens. This is what keeps the mic recorder's position in
    # the DOM stable across reruns — regardless of how many chat/audio
    # messages are rendered above it. A fixed-height, scrollable container
    # for history means the history list can grow/shrink without shifting
    # anything below it, and interaction_holder is the single, constant
    # slot where the recorder / live response / playback UI always live.
    # =========================================================================
    has_history = len(st.session_state.voice_chat_history) > 0

    if has_history:
        history_holder = st.container(height=420)
        st.write("---")
    else:
        history_holder = None

    interaction_holder = st.container()

    # 4. Render Conversation History Loop (inside the fixed-height box)
    if history_holder is not None:
        with history_holder:
            for msg in st.session_state.voice_chat_history:
                if msg["role"] == "user":
                    st.info(f"🗣️ **Mwanafunzi ({name}):** {msg['content']}")
                    if msg.get("audio_bytes"):
                        st.audio(msg["audio_bytes"], format="audio/wav")
                elif msg["role"] == "assistant":
                    st.success(f"🧙‍♂️ **Mwalimu:** {msg['content']}")
                    cached_audio = st.session_state.voice_cache.get(msg['content']) or msg.get("audio_bytes")
                    if cached_audio:
                        st.audio(cached_audio, format="audio/mp3")

    # =========================================================================
    # PIPELINE STAGE 1: IDLE (Render Recorder component and await speech)
    # =========================================================================
    if st.session_state.voice_stage == "idle":
        target_stt_lang = "sw" if "swahili" in str(language).lower() else "en"

        with interaction_holder:
            transcribed_text = speech_to_text(
                start_prompt="🎙️ Click & Start Speaking",
                stop_prompt="🛑 Stop & Send Voice Note",
                language=target_stt_lang,
                # Versioned key is intentional: it forces a fresh component
                # instance (and therefore a cleared return value) only when
                # a turn genuinely completes or history is cleared — not on
                # every rerun. Do NOT tie this to subject/topic changes.
                key=f"voice_stt_v_{st.session_state.voice_recorder_version}"
            )

        if transcribed_text:
            cleaned_text = str(transcribed_text).strip()
            cleaned_text = cleaned_text.replace("play music by", "").replace("play music", "").strip()

            if cleaned_text:
                # Freeze details into session state, move stage immediately to block double capture
                st.session_state.pending_user_text = cleaned_text
                st.session_state.voice_stage = "thinking"
                st.rerun()

    # =========================================================================
    # PIPELINE STAGE 2: THINKING (Execute LLM stream + TTS Processing)
    # =========================================================================
    elif st.session_state.voice_stage == "thinking":
        user_input = st.session_state.pending_user_text.strip()

        # Clean common speech recognition mistakes
        user_input = clean_math_transcript(user_input)

        # Remove accidental extra spaces
        user_input = " ".join(user_input.split())

        # 1. Instantly write user speech bubble into layout
        with interaction_holder:
            st.info(f"🗣️ **Mwanafunzi ({name}):** {user_input}")
            assistant_placeholder = st.empty()
            assistant_placeholder.markdown("🧙‍♂️ **Mwalimu AI is typing...**")

        # Isolate history window securely
        voice_history_payload = list(st.session_state.voice_chat_history)
        user_msg_dict = {"role": "user", "content": user_input, "is_voice": True, "audio_bytes": None}
        voice_history_payload.append(user_msg_dict)

        # 2. Database transaction for input logs
        save_voice_chat_message(
            student_uid=student_uid, student_name=name, grade=grade, age=int(age),
            subject=current_subject, role="user", message=user_input, audio_bytes=None
        )

        ai_response_text = ""
        try:
            adaptive_context = f"Voice Session. Subject: {subject}, Topic: {topic}"
            response_stream = ask_mwalimu_voice(
                question=user_input,
                student=voice_student_profile,
                messages=voice_history_payload,
                adaptive_context=adaptive_context,
                client=client
            )

            # Stream LLM Response safely
            for chunk in response_stream:
                if isinstance(chunk, str):
                    if not any(token in chunk for token in ["We need to", "Current context:", "Let's count:", "Under 50"]):
                        ai_response_text += chunk
                        assistant_placeholder.markdown(ai_response_text)
                    continue
                if hasattr(chunk, 'choices') and chunk.choices:
                    try:
                        delta_content = getattr(chunk.choices[0].delta, 'content', None)
                        if delta_content is not None:
                            delta_str = str(delta_content)
                            if "We need to" in delta_str or "Current context" in delta_str:
                                continue
                            ai_response_text += delta_str
                            assistant_placeholder.markdown(ai_response_text)
                    except:
                        continue

        except Exception as e:
            st.error(f"Error compiling response: {e}")
            st.session_state.voice_stage = "idle"
            st.rerun()

        # Clean metadata outputs out of string entirely before compilation
        ai_response_text = ai_response_text.replace("User Safety: safe", "").strip()

        if ai_response_text:
            with interaction_holder:
                with st.spinner("🔊 Generating Mwalimu's voice file..."):
                    try:
                        voice_target = "sw-KE-RafikiNeural" if "swahili" in str(language).lower() else "en-KE-AsiliaNeural"
                        audio_bytes_payload = generate_edge_tts_audio(ai_response_text, voice_target)

                        # Cache raw file binary mapping string content
                        st.session_state.voice_cache[ai_response_text] = audio_bytes_payload

                        # Add to persistent lists
                        st.session_state.voice_chat_history.append(user_msg_dict)
                        st.session_state.voice_chat_history.append({
                            "role": "assistant", "content": ai_response_text, "audio_bytes": audio_bytes_payload
                        })

                        # Save Assistant output to Data Layer
                        save_voice_chat_message(
                            student_uid=student_uid,
                            student_name=name,
                            grade=grade,
                            age=int(age),
                            subject=current_subject,
                            role="assistant",
                            message=ai_response_text,
                            audio_bytes=audio_bytes_payload
                        )

                        # Setup timer to block input while audio plays out
                        audio_duration = get_audio_duration(audio_bytes_payload)
                        st.session_state.playback_end_time = time.time() + audio_duration + 4.0  # 🚀 Added buffer
                        st.session_state.voice_stage = "speaking"

                    except Exception as tts_err:
                        st.error(f"TTS Error generation failed: {tts_err}")
                        st.session_state.voice_stage = "idle"

            # Clear inputs and rerun directly to play state
            st.session_state.pending_user_text = ""
            st.rerun()
        else:
            st.session_state.voice_stage = "idle"
            st.rerun()

    # =========================================================================
    # PIPELINE STAGE 3: SPEAKING (Autoplay active voice, lock recorder)
    # =========================================================================
    elif st.session_state.voice_stage == "speaking":
        with interaction_holder:
            if st.session_state.voice_chat_history:
                last_msg = st.session_state.voice_chat_history[-1]
                if last_msg["role"] == "assistant" and last_msg.get("audio_bytes"):
                    st.markdown("🧙‍♂️ **Mwalimu AI is speaking...**")
                    st.audio(last_msg["audio_bytes"], format="audio/mp3", autoplay=True)

            # Display a passive loader indicator while timer ticks down
            st.caption("⏳ Input locked until Mwalimu finishes reading context aloud.")

        time.sleep(1.0)  # 🚀 Increased checking sleep interval for stability
        st.rerun()

    # --- DEDICATED CONFIRMATION DIALOG MODAL ---
    @st.dialog("🗑️ Clear Voice Data")
    def confirm_clear_voice_dialog():
        current_subject = st.session_state.get("active_subject", "General Studies")
        st.warning(f"You are about to permanently delete all Voice Tutor conversations for **{current_subject}**.\n\nThis action cannot be undone.")
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if st.button("Yes, Clear History", use_container_width=True, type="primary"):
                clear_voice_chat_history_only(
                    student_uid=str(st.session_state.get("uid", "")),
                    grade=st.session_state.get("grade", "Grade 6"),
                    age=int(st.session_state.get("age", 12)),
                    subject=current_subject
                )
                st.session_state.voice_chat_history = []
                st.session_state.voice_cache = {}
                st.session_state.voice_stage = "idle"
                st.session_state.voice_recorder_version += 1
                st.toast("Voice database history records removed completely!")
                st.rerun()
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

    if len(st.session_state.voice_chat_history) > 0:
        st.write("")
        if st.button("🗑️ Permanently Delete Voice DB Logs", type="secondary"):
            confirm_clear_voice_dialog()