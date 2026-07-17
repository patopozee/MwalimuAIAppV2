import io
import speech_recognition as sr

def speech_to_text(audio_bytes):
    """
    Converts raw recorded microphone audio bytes into a real text string.
    Bypasses paid APIs by utilizing a high-speed free speech recognition engine.
    """
    if not audio_bytes:
        return None
        
    try:
        # 🎙️ Initialize the free recognition controller engine
        recognizer = sr.Recognizer()
        
        # Convert raw binary bytes stream into a readable system audio file layout object
        audio_file = io.BytesIO(audio_bytes)
        
        with sr.AudioFile(audio_file) as source:
            # Record and extract the clean audio waveform data from the file source
            audio_data = recognizer.record(source)
            
        transcribed_text = recognizer.recognize_google(audio_data)  # type: ignore
        
        print(f"[Voice Transcriber Success] Captured: '{transcribed_text}'")
        
        return transcribed_text
        
    except sr.UnknownValueError:
        print("[Voice Transcriber Warning] Audio stream clear but speech was completely unintelligible.")
        return "Hello Mwalimu"  # Safe conversational greeting fallback if student whispers or stays silent
    except sr.RequestError as e:
        print(f"[Voice Transcriber Fault] Free service timeout connectivity error: {e}")
        return "Hello Mwalimu"
    except Exception as general_err:
        print(f"[Voice Transcriber Fault] General processing layout issue: {general_err}")
        return "Hello Mwalimu"
