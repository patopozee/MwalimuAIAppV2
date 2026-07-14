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


# ---------------------------------------------------------------------
# 🚀 PERFORMANCE ENGINE CACHE CLEAR IMPLEMENTATION AUTOMATION
# ---------------------------------------------------------------------
def flush_all_database_caches():
    """Clears localized memory buffers on updates to maintain structural synchronization."""
    get_student_stats.clear()
    get_student_quiz_history.clear()
    get_next_difficulty.clear()
    get_student_learning_analysis.clear()
    get_chat_history.clear()
    get_student_data.clear()


def create_tables():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
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
                  subject="General", topics="General", sub_topic="General", learning_outcome="General"):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO progress (student_name, student_grade, student_age, activity_type, topic, score, subject, strand, sub_strand, learning_outcome)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_name, student_grade, int(student_age), activity_type, topic, score, subject, topics, sub_topic, learning_outcome))
    conn.commit()
    conn.close()
    flush_all_database_caches()  # 🎯 Instant RAM sync trigger


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


@st.cache_data(ttl=30, show_spinner=False)
def get_chat_history(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT activity_type, topic FROM progress
        WHERE student_name = ? AND student_grade = ? AND student_age = ?
        AND (activity_type = 'student' OR activity_type = 'assistant')
        ORDER BY id ASC
    """, (student_name, grade, int(age)))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": "user" if r[0] == "student" else "assistant", "content": r[1]} for r in rows]


def save_chat_message(student_name: str, grade: str, age: int, role: str, message: str):
    activity = "student" if role in ["user", "student"] else "assistant"
    save_activity(
        student_name=student_name, 
        student_grade=grade, 
        student_age=int(age),
        activity_type=activity, 
        topic=message, 
        score=0
    )


def clear_student_chat_history(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ?
        AND (activity_type = 'student' OR activity_type = 'assistant')
    """, (student_name, grade, int(age)))
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

