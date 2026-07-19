# services/database.py
import sqlite3
from config import DATABASE_NAME
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json  # Required to decode your string format
import streamlit as st
from datetime import datetime, timedelta
from google.cloud.firestore import FieldFilter

# Initialize the app safely using your custom single-string JSON string layout
if not firebase_admin._apps:
    raw_json_str = None
    try:
        # 1. Attempt Streamlit runtime access layer lookup
        if "firebase" in st.secrets and "service_account_json" in st.secrets["firebase"]:
            raw_json_str = st.secrets["firebase"]["service_account_json"]
    except Exception:
        pass

    # 2. Asynchronous background server fallback lookup context layer (e.g., Uvicorn runtime)
    if not raw_json_str:
        import toml
        secrets_path = os.environ.get("STREAMLIT_SECRETS_PATH", os.path.join(".streamlit", "secrets.toml"))
        if os.path.exists(secrets_path):
            try:
                config = toml.load(secrets_path)
                raw_json_str = config.get("firebase", {}).get("service_account_json")
            except Exception as e:
                print(f"⚠️ Failed to parse secrets toml parameters: {e}")

    # 3. Compile and initialize the Firebase credential map schema safely
    if raw_json_str:
        try:
            # Safely unroll the raw text configuration map directly from your string payload
            credentials_dict = json.loads(str(raw_json_str).strip())
            cred = credentials.Certificate(credentials_dict)
            firebase_admin.initialize_app(cred)
            app = firebase_admin.get_app()
        except Exception as json_err:
            raise ValueError(f"CRITICAL: Failed to decode service account string payload: {json_err}")
    else:
        # Ultimate fallback option if the configuration fields are entirely unpopulated
        raise FileNotFoundError("Could not locate any valid 'service_account_json' settings in secrets.toml.")

db = firestore.client()
if os.path.exists("/data"):
    #  PRODUCTION SERVER LINK (Locks directly to your secure GCP Bucket)
    DATABASE_NAME = "/data/mwalimu.db"
else:
    # 💻 LOCAL DEVELOPMENT FALLBACK (Saves safely inside your local root project folder)
    DATABASE_NAME = "mwalimu.db"


# ---------------------------------------------------------------------
# 🚀 PERFORMANCE ENGINE CACHE CLEAR IMPLEMENTATION AUTOMATION
# ---------------------------------------------------------------------
def flush_all_database_caches():
    """Clears localized memory buffers on updates to maintain structural synchronization."""
    get_student_stats.clear()
    get_student_quiz_history.clear()
    get_next_difficulty.clear()
    get_student_learning_analysis.clear()
    get_ask_mwalimu_history.clear()
    get_student_data.clear()


def create_tables():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # 1. Create the students table layout
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        grade TEXT,
        age INTEGER,
        favorite_subject TEXT,
        weak_subject TEXT,
        learning_style TEXT,
        language TEXT
    )
    """)
    
    # 2. Create the fully updated progress table layout
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        student_grade TEXT,
        student_age INTEGER,
        activity_type TEXT,
        topic TEXT,
        score INTEGER,
        subject TEXT,
        strand TEXT,
        sub_strand TEXT,
        learning_outcome TEXT,
        attachment TEXT,
        is_voice INTEGER DEFAULT 0,    -- 🎙️ Tracks if message is voice
        audio_bytes BLOB DEFAULT NULL,  -- 🎙️ Stores raw generated audio files
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Create the global admin knowledge base materials table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT,
        topic TEXT,
        sub_topic TEXT,
        filename TEXT,
        content TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # 🏫 LMS Tracker: Monitors lesson completion states and student mastery metrics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_uid TEXT NOT NULL,
        grade TEXT NOT NULL,
        subject TEXT NOT NULL,
        lesson_id TEXT NOT NULL,
        mastery_score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Not Started', -- 'Not Started', 'Learning', 'Completed'
        completed_at TIMESTAMP,
        time_spent_mins INTEGER DEFAULT 0,
        quiz_high_score INTEGER DEFAULT 0,
        UNIQUE(student_uid, subject, lesson_id)
    )
    """)

    
    # Save all table structures and close out the file handler transaction safely
    conn.commit()
    conn.close()



def save_student(student):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO students (name, grade, age, favorite_subject, weak_subject, learning_style, language)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (student["name"], student["grade"], student["age"], student["favorite_subject"],
          student["weak_subject"], student["learning_style"], student["language"]))
    conn.commit()
    conn.close()
    flush_all_database_caches()  # 🎯 Instant RAM sync trigger


def save_activity(student_name, student_grade, student_age, activity_type, topic, score=0,
                  subject="General", topics="General", sub_topic="General", 
                  learning_outcome="General", attachment=None, is_voice=0, audio_bytes=None): # <-- Add variables here
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    
    attachment_json = json.dumps(attachment) if attachment is not None else None

    
    cursor.execute("""
    INSERT INTO progress (student_name, student_grade, student_age, activity_type, topic, 
    score, subject, strand, sub_strand, learning_outcome, attachment, is_voice, audio_bytes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_name, student_grade, int(student_age), activity_type, topic, score, subject, 
          topics, sub_topic, learning_outcome, attachment_json, is_voice, audio_bytes)) # <-- Add mapping params here
    conn.commit()
    conn.close()
    flush_all_database_caches()




# ---------------------------------------------------------------------
# ⚡ READ CACHING OPTIMIZATIONS (RAM SPEED ENGINES)
# ---------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def get_student_stats(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # 1. Quizzes Count
    cursor.execute("""
        SELECT COUNT(*) FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'quiz_score'
    """, (student_name, grade, int(age)))
    quizzes = cursor.fetchone()[0]

    # 2. Questions Asked Count
    cursor.execute("""
        SELECT COUNT(*) FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'student'
    """, (student_name, grade, int(age)))
    questions = cursor.fetchone()[0]

    # 3. Average Score
    cursor.execute("""
        SELECT AVG(score) FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'quiz_score'
    """, (student_name, grade, int(age)))
    avg_score = cursor.fetchone()[0]
    avg_score = round(avg_score) if avg_score is not None else 0

    conn.close()
    return {"quizzes": quizzes, "questions": questions, "average_score": avg_score}


@st.cache_data(ttl=60, show_spinner=False)
def get_student_quiz_history(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT score FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'quiz_score'
        ORDER BY created_at ASC
    """, (student_name, grade, int(age)))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]


@st.cache_data(ttl=60, show_spinner=False)
def get_next_difficulty(student_name: str, grade: str, age: int, topic: str) -> str:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT score FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'quiz_score' AND topic = ?
        ORDER BY created_at DESC LIMIT 1
    """, (student_name, grade, int(age), topic))
    row = cursor.fetchone()
    conn.close()
    if row:
        last_score = row[0]
        if last_score >= 80: return "Hard"
        elif last_score >= 50: return "Medium"
        else: return "Easy"
    return "Medium"


@st.cache_data(ttl=60, show_spinner=False)
def get_student_learning_analysis(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT topic, AVG(score) FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'quiz_score'
        GROUP BY topic
    """, (student_name, grade, int(age)))
    topic_averages = cursor.fetchall()
    conn.close()
    
    weak_topics = [topic for topic, avg in topic_averages if avg < 50]
    strong_topics = [topic for topic, avg in topic_averages if avg >= 80]
    all_scores = [avg for topic, avg in topic_averages]
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    
    if overall_avg < 50: current_level = "Easy"
    elif overall_avg < 80: current_level = "Medium"
    else: current_level = "Hard"
    return {"weak_topics": weak_topics, "strong_topics": strong_topics, "current_level": current_level}


@st.cache_data(ttl=5)
def get_ask_mwalimu_history(student_name, grade, age):
    """Pulls text messages and their corresponding upload preview payload configurations safely."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT activity_type, topic, attachment FROM progress
        WHERE student_name=? AND student_grade=? AND student_age=?
        AND activity_type IN ('ask_user', 'ask_assistant')
        ORDER BY id
    """, (student_name, grade, age))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        role = "user" if row["activity_type"] == "ask_user" else "assistant"
        
        # Build standard base text dictionary matching your main.py structures
        msg_node = {
            "role": role,
            "content": row["topic"]
        }
        
        # If a valid attachment payload string exists, unpack its visual mappings!
        if row["attachment"]:
            try:
                attachment_data = json.loads(row["attachment"])
                if isinstance(attachment_data, dict):
                    if attachment_data.get("type") == "image_base64":
                        msg_node["image_preview"] = attachment_data.get("content")
                    elif attachment_data.get("type") == "text_extraction":
                        msg_node["file_preview"] = attachment_data.get("filename")
            except Exception:
                pass  # Avoid history loop breaks if an individual block fails decoding
                
        history.append(msg_node)
        
    return history


@st.cache_data(ttl=5)
def get_voice_chat_history(student_name, grade, age):
    """Pulls vocal histories and structural attachments with high-efficiency query caching."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Explicitly add attachment to the columns selection query
    cursor.execute("""
        SELECT activity_type, topic, audio_bytes, attachment FROM progress
        WHERE student_name=? AND student_grade=? AND student_age=?
        AND activity_type IN ('voice_user', 'voice_assistant')
        ORDER BY id
    """, (student_name, grade, age))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        role = "user" if row["activity_type"] == "voice_user" else "assistant"
        
        msg_node = {
            "role": role,
            "content": row["topic"],
            "audio_bytes": row["audio_bytes"],
            "is_voice": True
        }
        
        # Safely unroll potential attachments into matching visual dictionary flags
        if row["attachment"]:
            try:
                attachment_data = json.loads(row["attachment"])
                if isinstance(attachment_data, dict):
                    if attachment_data.get("type") == "image_base64":
                        msg_node["image_preview"] = attachment_data.get("content")
                    elif attachment_data.get("type") == "text_extraction":
                        msg_node["file_preview"] = attachment_data.get("filename")
            except Exception:
                pass  # Skip corrupted rows without breaking the loop
                
        history.append(msg_node)
        
    return history



def save_ask_mwalimu_message(student_name, grade, age, role, message, attachment=None):
    """Saves a conversational chat message entry exactly once along with any attachments."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Correctly parse database role mappings matching your system
    activity = "ask_user" if role == "user" else "ask_assistant"
    
    # Serialize attachments dictionary safely to a string payload if present
    attachment_json = json.dumps(attachment) if attachment else None
    
    cursor.execute("""
        INSERT INTO progress (
            student_name, 
            student_grade, 
            student_age, 
            activity_type, 
            topic, 
            attachment, 
            is_voice
        ) VALUES (?, ?, ?, ?, ?, ?, 0)
    """, (student_name, grade, int(age), activity, message, attachment_json))
    
    conn.commit()
    conn.close()
    
    # Instantly clear read caches so updates show up in real-time
    get_ask_mwalimu_history.clear()


def save_voice_chat_message(
    student_name,
    grade,
    age,
    role,
    message,
    audio_bytes=None
):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    activity = "voice_user" if role == "user" else "voice_assistant"

    cursor.execute("""
        INSERT INTO progress
        (
            student_name,
            student_grade,
            student_age,
            activity_type,
            topic,
            is_voice,
            audio_bytes
        )
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """,
    (
        student_name,
        grade,
        age,
        activity,
        message,
        audio_bytes
    ))

    conn.commit()
    conn.close()

    get_voice_chat_history.clear()



def clear_student_chat_history(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""        
        DELETE FROM progress
        WHERE student_name=?
        AND student_grade=?
        AND student_age=?
        AND activity_type IN
        (
            'ask_user',
            'ask_assistant'
        )
        """,
        (student_name, grade, int(age)))
    conn.commit()
    conn.close()
    flush_all_database_caches()  # 🎯 Wipe old historical cache metrics mapping frames


@st.cache_data(ttl=120, show_spinner=False)
def get_student_data(uid):
    """Retrieves student profile from Firestore with high-performance query caching."""
    try:
        # 1. Attempt direct ID lookup
                # 1. Attempt direct ID lookup
        doc_ref = db.collection('users').document(str(uid))
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
            
        # 2. Fallback to searching the 'email' field
        query = db.collection('users').where(filter=FieldFilter('email', '==', uid)).stream()
        for user_doc in query:
            return user_doc.to_dict()
        return None
    except Exception:
        return None


def upgrade_user_tier(uid, new_tier):
    """Updates the user tier and sets a 30-day subscription expiry in Firestore."""
    try:
        calculated_expiry = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        live_subscription = {
            "tier": str(new_tier).strip(),
            "expiry_date": calculated_expiry,
            "payment_status": "Completed",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Query to look up by email first, matching old patterns
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', uid).stream()
        doc_found = False
        for doc in query:
            doc_found = True
            db.collection('users').document(doc.id).update({
                "subscription": live_subscription
            })
            break
            
        # Direct fallback ID update if no query parameters match
        if not doc_found:
            print(f"DEBUG: User not found: {uid}")
            
        # 🎯 FORCE PROFILE CACHE RESET: Clear out old cache data so user updates load instantly
        get_student_data.clear()
    except Exception as e:
        print(f"An error occurred while updating Firestore: {e}")


def save_support_message(name: str, email: str, subject: str, message: str) -> bool:
    """Saves an inbound landing page inquiry directly into Firestore support collection."""
    try:
        support_payload = {
            "name": name.strip(),
            "email": email.strip().lower(),
            "subject": subject.strip(),
            "message": message.strip(),
            "status": "Open",
            "created_at": datetime.utcnow().isoformat()
        }
        # Appends a unique auto-generated ID entry snapshot inside collections branch
        db.collection('support_messages').add(support_payload)
        return True
    except Exception as e:
        print(f" Failed to submit message payload structure: {str(e)}")
        return False

def clear_voice_chat_history_only(student_name: str, grade: str, age: int):
    """Purges only voice records and audio bytes for the student profile."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Strictly deletes voice_user and voice_assistant rows
    cursor.execute("""
        DELETE FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ?
        AND activity_type IN ('voice_user', 'voice_assistant')
    """, (student_name, grade, int(age)))
    
    conn.commit()
    conn.close()
    
    # Reset only the voice read cache
    if hasattr(get_voice_chat_history, "clear"):
        get_voice_chat_history.clear()

def save_admin_material(subject, topic, sub_topic, filename, content):
    """Saves or updates global teaching material in the system."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM admin_materials 
        WHERE subject=? AND topic=? AND sub_topic=? AND filename=?
    """, (subject, topic, sub_topic, filename))
    
    cursor.execute("""
        INSERT INTO admin_materials (subject, topic, sub_topic, filename, content)
        VALUES (?, ?, ?, ?, ?)
    """, (subject, topic, sub_topic, filename, content))
    conn.commit()
    conn.close()
    
    # 🔥 FORCE RESET WALIMU'S MEMORY TO CAPTURE THE NEW UPLOAD IMMEDIATELY
    if hasattr(get_admin_material_context, "clear"):
        get_admin_material_context.clear()

#  Add the caching decorator here so it can be cleared dynamically
@st.cache_data(ttl=600)
def get_admin_material_context(subject, topic, sub_topic=None):
    """Retrieves all global reference texts matching the current lesson context."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    if sub_topic:
        cursor.execute("""
            SELECT filename, content FROM admin_materials 
            WHERE subject=? AND topic=? AND sub_topic=?
        """, (subject, topic, sub_topic))
    else:
        cursor.execute("""
            SELECT filename, content FROM admin_materials 
            WHERE subject=? AND topic=?
        """, (subject, topic))
        
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return ""
        
    context_str = "\n\n=== ADMIN UPLOADED REFERENCE MATERIALS ==="
    for row in rows:
        context_str += f"\n\n[File: {row[0]}]\n{row[1]}"
    return context_str
def get_all_admin_materials():
    """Fetches a list of all globally uploaded admin reference books and materials."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 🌟 FIXED: Explicitly pull the full 'content' string right here
    cursor.execute("""
        SELECT id, subject, topic, sub_topic, filename, content, uploaded_at 
        FROM admin_materials 
        ORDER BY uploaded_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_admin_material_by_id(material_id: int):
    """Deletes a specific reference document row out of the knowledge base completely."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM admin_materials WHERE id = ?", (material_id,))
    conn.commit()
    conn.close()
    
    # 🔥 Wipes the memory layer cache instantly so the AI drops references immediately
    if hasattr(get_admin_material_context, "clear"):
        get_admin_material_context.clear()

def get_all_student_lms_progress():
    """Fetches a relational overview of all students and their active lesson progress stats."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Left join ensures we see the student's base profile even if they haven't started a lesson node yet
    cursor.execute("""
        SELECT 
            s.name as student_name,
            s.grade as student_grade,
            p.subject,
            p.lesson_id,
            p.status,
            p.quiz_high_score,
            p.completed_at
        FROM students s
        LEFT JOIN student_progress p ON s.id = p.student_uid
        ORDER BY p.completed_at DESC, s.name ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows





