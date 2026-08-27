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
    Builds lesson order directly from the curriculum files safely.
    """
    if not grade:
        return {"lessons": []}

    # Normalize grade format (e.g., convert "6" or "grade 6" to "Grade 6")
    grade_str = str(grade).strip().title()
    if not grade_str.startswith("Grade") and grade_str.isdigit():
        grade_str = f"Grade {grade_str}"

    grade_data = CURRICULUM.get(grade_str)

    # Check if grade_data is valid before calling .get()
    if not isinstance(grade_data, dict):
        return {"lessons": []}

    subject_tree = grade_data.get(subject)

    if not isinstance(subject_tree, dict):
        return {"lessons": []}

    return {
        "lessons": build_course_from_curriculum(subject_tree)
    }

def get_student_lesson_progress(student_uid: str, grade: str, subject: str, lesson_id: str):
    """Fetches the active milestone tracking state for an individual lesson module."""
    import sqlite3
    from services.database import DATABASE_NAME
    
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 🎯 FIX: Matches your clean column variables perfectly
    cursor.execute("""
        SELECT status, mastery_score, quiz_high_score 
        FROM student_progress 
        WHERE student_uid = ? AND grade = ? AND subject = ? AND lesson_id = ?
    """, (str(student_uid), str(grade), str(subject), str(lesson_id)))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    
    # Fallback state if the unit has never been accessed by the learner
    return {"status": "Not Started", "mastery_score": 0, "quiz_high_score": 0}

def start_or_update_lesson(student_uid: str, student_name: str, grade: str, subject: str, lesson_id: str, status="Learning"):
    """Initializes or updates a lesson state machine transaction record securely."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # 🎯 FIXED: Added missing comma, added 6th value binding slot, and included student_name
    cursor.execute("""
        INSERT INTO student_progress (student_uid, student_name, grade, subject, lesson_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_uid, subject, lesson_id) 
        DO UPDATE SET 
            student_name = EXCLUDED.student_name,
            status = EXCLUDED.status
        WHERE status != 'Completed'
    """, (str(student_uid), str(student_name), str(grade), str(subject), str(lesson_id), str(status)))
    
    conn.commit()
    conn.close()

def complete_student_lesson(student_uid: str, student_name: str, grade: str, subject: str, 
    lesson_id: str, mastery: int, quiz_score: int):
    """Marks a targeted learning objective node as complete and handles leaderboard inclusion."""
    from services.database import create_leaderboard_table
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Update standard student progress tracker
    cursor.execute("""
    INSERT INTO student_progress (
        student_uid, student_name, grade, subject, lesson_id, 
        mastery_score, status, quiz_high_score, completed_at
    )
    VALUES (?, ?, ?, ?, ?, ?, 'Completed', ?, ?)
    ON CONFLICT(student_uid, subject, lesson_id) 
    DO UPDATE SET 
        student_name = EXCLUDED.student_name,
        mastery_score = CASE WHEN EXCLUDED.mastery_score > student_progress.mastery_score THEN EXCLUDED.mastery_score ELSE student_progress.mastery_score END,
        quiz_high_score = CASE WHEN EXCLUDED.quiz_high_score > student_progress.quiz_high_score THEN EXCLUDED.quiz_high_score ELSE student_progress.quiz_high_score END,
        status = 'Completed',
        completed_at = COALESCE(student_progress.completed_at, EXCLUDED.completed_at)
    """, (
        str(student_uid), str(student_name), str(grade), str(subject), 
        str(lesson_id), int(mastery), int(quiz_score), now_str
    ))
    conn.commit()
    conn.close()

    # 2. Add to leaderboard if score hits mastery of 70% or more
    if int(mastery) >= 70:
        create_leaderboard_table()  # Ensures table exists safely
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # We fetch student age safely from the profile context if needed, defaulting to 0 here
        student_age = 0 
        
        cursor.execute("""
        INSERT INTO leaderboard (
            student_uid, student_name, student_grade, student_age, 
            activity_type, topic, score, subject, created_at
        )
        VALUES (?, ?, ?, ?, 'quiz_score', ?, ?, ?, ?)
        """, (
            str(student_uid), str(student_name), str(grade), int(student_age),
            str(lesson_id), int(quiz_score), str(subject), now_str
        ))
        conn.commit()
        conn.close()


# --- UPDATE THIS LOGIC AT THE BOTTOM OF PAGE 6 & TOP OF PAGE 7 ---
def get_current_active_lesson(student_uid: str, grade: str, subject: str):
    """
    Identifies exactly which lesson element nodes the student is currently on.
    Safely returns None when the entire curriculum track is finished.
    """
    course = load_course_structure(grade, subject)
    lessons = course.get("lessons", [])
    
    if not lessons:
        return None
        
    for lesson in lessons:
        state = get_student_lesson_progress(student_uid, grade, subject, lesson["lesson_id"])
        # If an uncompleted lesson is encountered, immediately target it as active
        if state["status"] != "Completed":
            return lesson
            
    # 🎯 FIXED: When all units are mastered, return None to trigger the certificate UI path
    return None 


def unlock_next_lesson(student_uid: str, student_name: str, grade: str, subject: str, current_lesson_id: str):
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
        
        # 🎯 FIXED: Now safely passes the required student_name argument
        start_or_update_lesson(
            student_uid=student_uid,
            student_name=student_name,  # Forward the name token here!
            grade=grade,
            subject=subject,
            lesson_id=next_lesson["lesson_id"],
            status="Not Started"
        )
        return next_lesson
    return None


def generate_completion_certificate(student_uid: str, student_name: str, grade: str, subject: str):
    """Generates a premium completion certificate, pulling or creating frozen serial numbers from SQLite."""
    import io
    import time
    import random
    import os
    import sqlite3
    import qrcode
    from qrcode.image.pil import PilImage
    from reportlab.lib.pagesizes import A4, landscape  
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Line
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from services.database import DATABASE_NAME

    pdf_buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A4),
        rightMargin=30, leftMargin=30,
        topMargin=25, bottomMargin=25
    )
    
    # =========================================================
    # 🔒 SQLITE DATABASE DATA INTEGRITY FETCH OR LOCK
    # =========================================================
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cert_serial, cert_date FROM student_progress 
        WHERE student_uid = ? AND grade = ? AND subject = ?
    """, (str(student_uid), str(grade), str(subject)))
    
    row = cursor.fetchone()
    
    if row and row[0] is not None and row[1] is not None:
        # A saved certificate exists! Use the exact historical metrics
        cert_number = row[0]
        issue_date = row[1]
    else:
        # No saved certificate found. Create a permanent record for the first time
        timestamp = int(time.time())
        rand_seq = random.randint(1000, 9999)
        cert_number = f"MW-AI-{timestamp}-{rand_seq}"
        issue_date = time.strftime("%B %d, %Y")
        
        # Save these values directly into the active lesson transaction matrix mapping
        cursor.execute("""
            UPDATE student_progress 
            SET cert_serial = ?, cert_date = ?
            WHERE student_uid = ? AND grade = ? AND subject = ?
        """, (cert_number, issue_date, str(student_uid), str(grade), str(subject)))
        conn.commit()
        
    conn.close()
    
    # ---------------------------------------------------------
    # 🎨 EXACT FONT REGISTRATION SYSTEM
    # ---------------------------------------------------------
    cloister_font_path = "assets/fonts/CloisterBlack.ttf"
    lucida_font_path = "assets/fonts/LHANDW.TTF"
    
    title_font_name = 'Helvetica-Bold'
    name_font_name = 'Helvetica-Bold'
    
    if os.path.exists(cloister_font_path):
        pdfmetrics.registerFont(TTFont('CloisterBlack', cloister_font_path))
        title_font_name = 'CloisterBlack'
        
    if os.path.exists(lucida_font_path):
        pdfmetrics.registerFont(TTFont('LucidaHandwriting', lucida_font_path))
        name_font_name = 'LucidaHandwriting'

    # ---------------------------------------------------------
    # 📲 IN-MEMORY QR CODE GENERATOR SYSTEM
    # ---------------------------------------------------------
    qr_payload = f"URL: ://mwalimuaiapp.com\nStudent: {student_name}\nSerial: {cert_number}"
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    
    qr_img_buffer = io.BytesIO()
    qr_pil_img = qr.make_image(image_factory=PilImage, fill_color="#101726", back_color="white")
    qr_pil_img.save(qr_img_buffer, format="PNG")
    qr_img_buffer.seek(0)
    
    qr_element = Image(qr_img_buffer, width=65, height=65)

    # DESIGN FRAME SYSTEM (Canvas Background Painting Layer - CLEAN NO WATERMARK)
    def draw_certificate_background(canvas, doc):
        canvas.saveState()
        canvas.setFillAlpha(1.0)
        
        # Thick Outer Corporate Frame Border Lines
        canvas.setStrokeColor(colors.HexColor("#101726"))
        canvas.setLineWidth(10)
        canvas.rect(15, 15, doc.width + 30, doc.height + 40)
        
        # Inner Accent Pin-Stripe Frame Line in Mwalimu Blue
        canvas.setStrokeColor(colors.HexColor("#2473F2"))
        canvas.setLineWidth(2.0)
        canvas.rect(25, 25, doc.width + 10, doc.height + 20)
        
        # Decorative Left Corner Accent blocks
        canvas.setFillColor(colors.HexColor("#101726"))
        canvas.rect(15, 15, 180, 24, fill=True, stroke=False)
        canvas.setFillColor(colors.HexColor("#2473F2"))
        canvas.rect(195, 15, 90, 24, fill=True, stroke=False)
        canvas.restoreState()

    styles = getSampleStyleSheet()
    
    # Typography Styles Mapping System
    title_style = ParagraphStyle('CertTitle', parent=styles['Normal'], fontName=title_font_name, fontSize=55, leading=50, textColor=colors.HexColor("#101726"), alignment=1, spaceAfter=12)
    subtext_style = ParagraphStyle('CertSubText', parent=styles['Normal'], fontName='Helvetica', fontSize=14, leading=18, textColor=colors.HexColor("#64748B"), alignment=1, spaceAfter=18)
    name_style = ParagraphStyle('CertStudentName', parent=styles['Normal'], fontName=name_font_name, fontSize=38, leading=46, textColor=colors.HexColor("#2473F2"), alignment=1, spaceAfter=18)
    body_style = ParagraphStyle('CertBodyText', parent=styles['Normal'], fontName='Helvetica', fontSize=14, leading=26, textColor=colors.HexColor("#334155"), alignment=1, spaceAfter=25)
    footer_lbl_style = ParagraphStyle('CertFooterLbl', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#101726"), alignment=1)
    footer_val_style = ParagraphStyle('CertFooterVal', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=13, textColor=colors.HexColor("#64748B"), alignment=1)
    ceo_name_style = ParagraphStyle('CertCeoName', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor("#101726"), alignment=1)
    ceo_title_style = ParagraphStyle('CertCeoTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=13, textColor=colors.HexColor("#64748B"), alignment=1)

    story = []
    
    # Logo Head Placement
    logo_path = "assets/cert_logo.png" 
    if os.path.exists(logo_path):
        story.append(Image(logo_path, width=300, height=95, kind='proportional'))
        story.append(Spacer(1, 10))
    else:
        story.append(Spacer(1, 30))

    # Branding Text
    story.append(Paragraph("Certificate of Course Completion", title_style))
    story.append(Paragraph("This official award document is proudly presented to", subtext_style))
    story.append(Paragraph(student_name, name_style)) 
    
    course_narrative = (
        f"for successfully completing all curriculum lesson units, diagnostic mastery evaluations, "
        f"and structured challenge frameworks assigned under the <b>{subject}</b> domain "
        f"at the <b>{grade}</b> execution tier verified via the Mwalimu AI platform engines."
    )
    story.append(Paragraph(course_narrative, body_style))
    story.append(Spacer(1, 15))
    
    # Signature Asset
    sig_path = "assets/signature.png"
    if os.path.exists(sig_path):
        sig_element = Image(sig_path, width=250, height=60, kind='proportional')
    else:
        sig_script_style = ParagraphStyle('CertSignScript', parent=styles['Normal'], fontName='Times-BoldItalic', fontSize=18, leading=22, textColor=colors.HexColor("#0F172A"), alignment=1)
        sig_element = Paragraph("<i>Mwalimu AI Director</i>", sig_script_style)

    # Vector Rows Lines
    d_line = Drawing(doc.width, 2)
    d_line.add(Line(20, 0, 280, 0, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=1))
    d_line.add(Line(doc.width - 280, 0, doc.width - 20, 0, strokeColor=colors.HexColor("#CBD5E1"), strokeWidth=1))
    story.append(d_line)
    story.append(Spacer(1, 4))
    
    # Structural Table Grid Row 1
    graphics_table_data = [[sig_element, "", qr_element]]
    graphics_table = Table(graphics_table_data, colWidths=[300, doc.width - 600, 300])
    graphics_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(graphics_table)
    story.append(Spacer(1, 4))
    
    # Structural Table Grid Row 2
    footer_table_data = [
        [
            [Paragraph("Patrick Wachira Mugo", ceo_name_style), Spacer(1, 2), Paragraph("CEO Mwalimu AI App", ceo_title_style)], 
            "", 
            [Paragraph(cert_number, footer_lbl_style), Spacer(1, 2), Paragraph(f"Official Security Tracking ID • Issued: {issue_date}", footer_val_style)]
        ]
    ]
    
    footer_table = Table(footer_table_data, colWidths=[300, doc.width - 600, 300])
    footer_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0), ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(footer_table)
    
    doc.build(story, onFirstPage=draw_certificate_background)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes



def get_lms_statistics(student_uid, grade, subject):

    # Number of lessons in the curriculum
    course = load_course_structure(grade, subject)
    total_lessons = len(course["lessons"])

    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(CASE WHEN status='Completed' THEN 1 END),
            AVG(quiz_high_score),
            MAX(mastery_score)
        FROM student_progress
        WHERE student_uid = ?
          AND grade = ?
          AND subject = ?
    """, (student_uid, grade, subject))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        row = (0, 0, 0)

    completed_lessons, average_score, mastery = row

    completed_lessons = completed_lessons or 0
    average_score = round(average_score or 0)
    mastery = mastery or 0

    completion = (
        round((completed_lessons / total_lessons) * 100)
        if total_lessons > 0 else 0
    )

    return {
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
        "completion": completion,
        "average_score": average_score,
        "mastery": mastery,
    }

def get_lms_learning_analysis(student_uid: str, subject: str):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            lesson_id,
            mastery_score,
            status
        FROM student_progress
        WHERE student_uid = ?
        AND subject = ?
    """, (student_uid, subject))

    rows = cursor.fetchall()
    conn.close()

    weak_topics = []
    strong_topics = []

    for lesson_id, mastery, status in rows:

        lesson_name = lesson_id.replace("_", " ").title()

        if status == "Completed":
            strong_topics.append(lesson_name)

        elif mastery < 70:
            weak_topics.append(lesson_name)

    return {
        "weak_topics": weak_topics,
        "strong_topics": strong_topics,
    }

def get_lms_quiz_history(student_uid: str, subject: str):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT quiz_high_score
        FROM student_progress
        WHERE student_uid = ?
        AND subject = ?
        AND status = 'Completed'
        ORDER BY completed_at ASC
    """, (student_uid, subject))

    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows if row[0] is not None]