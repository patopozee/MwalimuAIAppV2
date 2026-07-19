import json
import os
import sqlite3
from datetime import datetime
from services.database import DATABASE_NAME
from curriculum.grade1 import GRADE_1
from curriculum.grade2 import GRADE_2
from curriculum.grade3 import GRADE_3
from curriculum.grade4 import GRADE_4
from curriculum.grade5 import GRADE_5
from curriculum.grade6 import GRADE_6
from curriculum.grade7 import GRADE_7
from curriculum.grade8 import GRADE_8
from curriculum.grade9 import GRADE_9
from curriculum.grade10 import GRADE_10
from curriculum.grade11 import GRADE_11
from curriculum.grade12 import GRADE_12

CURRICULUM = {
    "Grade 1": GRADE_1,
    "Grade 2": GRADE_2,
    "Grade 3": GRADE_3,
    "Grade 4": GRADE_4,
    "Grade 5": GRADE_5,
    "Grade 6": GRADE_6,
    "Grade 7": GRADE_7,
    "Grade 8": GRADE_8,
    "Grade 9": GRADE_9,
    "Grade 10": GRADE_10,
    "Grade 11": GRADE_11,
    "Grade 12": GRADE_12,
}

if os.path.exists("/data"):
    #  PRODUCTION SERVER LINK (Locks directly to your secure GCP Bucket)
    DATABASE_NAME = "/data/mwalimu.db"
else:
    # 💻 LOCAL DEVELOPMENT FALLBACK (Saves safely inside your local root project folder)
    DATABASE_NAME = "mwalimu.db"

def build_course_from_curriculum(subject_tree):
    """
    Converts the curriculum hierarchy into an ordered lesson list.
    """

    lessons = []

    order = 1

    for topic, subtopics in subject_tree.items():

        for subtopic, learning_outcomes in subtopics.items():

            lessons.append({
                "lesson_id": subtopic.lower().replace(" ", "_"),
                "title": subtopic,
                "topic": topic,
                "order_index": order
            })

            order += 1

    return lessons


def load_course_structure(grade, subject):
    """
    Builds lesson order directly from the curriculum files.
    """

    grade_data = CURRICULUM.get(grade)

    if not grade_data:
        return {"lessons": []}

    subject_tree = grade_data.get(subject)

    if not subject_tree:
        return {"lessons": []}

    return {
        "lessons": build_course_from_curriculum(subject_tree)
    }

def get_student_lesson_progress(student_uid: str, grade: str, subject: str, lesson_id: str):
    """Pulls execution tracking metrics using standard subject and lesson_id variables."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM student_progress 
        WHERE student_uid = ? AND grade = ? AND subject = ? AND lesson_id = ?
    """, (str(student_uid), str(grade), str(subject), str(lesson_id)))
    
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"status": "Not Started", "mastery_score": 0, "quiz_high_score": 0}

def start_or_update_lesson(student_uid: str, grade: str, subject: str, lesson_id: str, status="Learning"):
    """Initializes or updates a lesson state machine transaction record securely."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO student_progress (student_uid, grade, subject, lesson_id, status)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(student_uid, subject, lesson_id) 
        DO UPDATE SET status = EXCLUDED.status
        WHERE status != 'Completed'
    """, (str(student_uid), str(grade), str(subject), str(lesson_id), str(status)))
    
    conn.commit()
    conn.close()

def complete_student_lesson(student_uid: str, grade: str, subject: str, lesson_id: str, mastery: int, quiz_score: int):
    """Marks a targeted learning objective node as complete using standard keys."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        INSERT INTO student_progress (student_uid, grade, subject, lesson_id, mastery_score, status, quiz_high_score, completed_at)
        VALUES (?, ?, ?, ?, ?, 'Completed', ?, ?)
        ON CONFLICT(student_uid, subject, lesson_id) 
        DO UPDATE SET 
            mastery_score = MAX(mastery_score, EXCLUDED.mastery_score),
            quiz_high_score = MAX(quiz_high_score, EXCLUDED.quiz_high_score),
            status = 'Completed',
            completed_at = COALESCE(completed_at, EXCLUDED.completed_at)
    """, (str(student_uid), str(grade), str(subject), str(lesson_id), int(mastery), int(quiz_score), now_str))
    
    conn.commit()
    conn.close()

def get_current_active_lesson(student_uid: str, grade: str, subject: str):
    """Identifies exactly which lesson element nodes the student is currently on."""
    course = load_course_structure(grade, subject)
    lessons = course.get("lessons", [])
    
    if not lessons:
        return None
        
    for lesson in lessons:
        state = get_student_lesson_progress(student_uid, grade, subject, lesson["lesson_id"])
        if state["status"] != "Completed":
            return lesson
            
    return lessons[-1] if lessons else None

def unlock_next_lesson(student_uid: str, grade: str, subject: str, current_lesson_id: str):
    """Calculates the subsequent lesson node configuration using standard curriculum keys."""
    course_structure = load_course_structure(grade, subject)
    lessons_list = course_structure.get("lessons", [])
    
    current_index = -1
    for idx, les in enumerate(lessons_list):
        if les["lesson_id"] == current_lesson_id:
            current_index = idx
            break
            
    if current_index != -1 and (current_index + 1) < len(lessons_list):
        next_lesson = lessons_list[current_index + 1]
        start_or_update_lesson(
            student_uid=student_uid,
            grade=grade,
            subject=subject,
            lesson_id=next_lesson["lesson_id"],
            status="Not Started"
        )
        return next_lesson
    return None

def generate_completion_certificate(student_name: str, grade: str, subject: str):
    """Generates an elegant, printable PDF Course Completion Certificate using ReportLab."""
    import io
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    
    pdf_buffer = io.BytesIO()
    
    # Create a clean landscape orientation certificate layout template sheet
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(letter),
        rightMargin=54, leftMargin=54,
        topMargin=54, bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom certificate typography styles
    title_style = ParagraphStyle(
        'CertTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=32, leading=38,
        textColor=HexColor('#1E88E5'), alignment=1, spaceAfter=20
    )
    subtitle_style = ParagraphStyle(
        'CertSub', parent=styles['Normal'],
        fontName='Helvetica', fontSize=14, leading=18,
        textColor=HexColor('#64748B'), alignment=1, spaceAfter=30
    )
    name_style = ParagraphStyle(
        'CertName', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=26, leading=32,
        textColor=HexColor('#0F172A'), alignment=1, spaceAfter=20
    )
    detail_style = ParagraphStyle(
        'CertDetail', parent=styles['Normal'],
        fontName='Helvetica', fontSize=12, leading=16,
        textColor=HexColor('#334155'), alignment=1
    )
    
    story = [
        Spacer(1, 40),
        Paragraph("CERTIFICATE OF COURSE COMPLETION", title_style),
        Paragraph("This official award document is proudly presented to", subtitle_style),
        Paragraph(student_name.upper(), name_style),
        Paragraph(f"for successfully completing all curriculum lesson units and diagnostic mastery evaluations", subtitle_style),
        Spacer(1, 10),
        Paragraph(f"<b>Course Domain:</b> {subject} | <b>Academic Level:</b> {grade}", detail_style),
        Paragraph(f"Verified via Mwalimu AI CBC Curriculum Guardrails Engine", detail_style),
        Spacer(1, 40)
    ]
    
    doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes
