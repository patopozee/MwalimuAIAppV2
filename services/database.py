# services/database.py
import sqlite3
from config import DATABASE_NAME
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime, timedelta
from google.cloud.firestore import FieldFilter

# Initialize the app only once
if not firebase_admin._apps:
    # Use the path to the file you just created
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

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

def get_student_stats(student_name: str, grade: str, age: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # 1. Quizzes Count
    cursor.execute("""
        SELECT COUNT(*) FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ? AND activity_type = 'quiz_score'
    """, (student_name, grade, int(age)))
    quizzes = cursor.fetchone()[0]

    # 2. Questions Asked Count (FIXED: Filter accurately on student input roles)
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

def get_chat_history(student_name: str, grade: str, age: int):
    """Retrieves chat history precisely filtered by the composite keys of Name, Grade, and Age."""
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
    """Saves incoming messages utilizing composite targeting credentials."""
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
    """Wipes historical chat context without impacting analytics records."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM progress 
        WHERE student_name = ? AND student_grade = ? AND student_age = ?
        AND (activity_type = 'student' OR activity_type = 'assistant')
    """, (student_name, grade, int(age)))
    conn.commit()
    conn.close()

def get_student_data(uid):
    """Retrieves student profile and prints progress to terminal."""
    try:
        
        # 1. Attempt direct ID lookup
        doc_ref = db.collection('users').document(str(uid))
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            return data
        
        # 2. Fallback to searching the 'email' field
        query = db.collection('users').where(filter=FieldFilter('email', '==', uid)).stream()
        
        for user_doc in query:
            data = user_doc.to_dict()
            return data
                
        return None
    except Exception as e:
        return None
    
def upgrade_user_tier(uid, new_tier):
    """Updates the user tier and sets a 30-day subscription expiry in Firestore."""
    try:
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', uid).stream()
        
        # Calculate 30-day expiry
        expiry_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")
        subscription_data = {
            "tier": new_tier,
            "start_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "expiry_date": expiry_date
        }
        
        user_found = False
        for doc in query:
            # Update tier AND add the subscription object
            doc.reference.update({
                'tier': new_tier,
                'subscription': subscription_data
            })
            user_found = True
            print(f"Successfully upgraded {uid} to {new_tier}. Expiry: {expiry_date}")
            
        if not user_found:
            print(f"DEBUG: User not found: {uid}")
            
    except Exception as e:
        print(f"An error occurred while updating Firestore: {e}")

