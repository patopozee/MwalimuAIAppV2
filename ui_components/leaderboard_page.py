import streamlit as st
import sqlite3
from services.database import DATABASE_NAME, get_grade_leaderboard

def get_single_student_progress_metrics(student_id_or_uid):
    """Fetches a detailed curriculum progress ledger specifically for the logged-in student profile."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Works perfectly by matching your progress table's student_uid field with the active session token
    cursor.execute("""
        SELECT 
            subject,
            lesson_id,
            status,
            quiz_high_score,
            completed_at
        FROM student_progress 
        WHERE student_uid = ?
        ORDER BY completed_at DESC, subject ASC
    """, (str(student_id_or_uid),))
    rows = cursor.fetchall()
    conn.close()
    return rows

def render_student_leaderboard_page():
    st.title("🏆 Mwalimu AI Analytics Hub & Leaderboard")
    st.write("Track your personalized curriculum progress goals and view national academic rankings across Kenya [INDEX].")
    st.write("---")

    # Fetch active logged-in student parameters safely out of the application memory context
    student_uid = str(st.session_state.get("uid") or "")
    student_name = str(st.session_state.get("student_name", "Student"))
    student_grade = str(st.session_state.get("grade", "Grade 6"))

    #=======
        # ====================================================================
    # 🕵️‍♂️ AUTOMATED DATA-SYNC DIAGNOSTIC INSPECTOR
    # ====================================================================
    with st.expander("🕵️‍♂️ Database Key Alignment Debugger (Click to Expand)"):
        st.write(f"**Active Session UID String:** `{student_uid}`")
        
        # Pull raw rows straight out of your database to see exactly what keys look like
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Peek at the last registered student row
        cursor.execute("SELECT id, name FROM students ORDER BY id DESC LIMIT 1")
        student_peek = cursor.fetchone()
        if student_peek:
            st.write(f"**Last Registered Student in DB:** ID/UID Field = `{student_peek['id']}` | Name = `{student_peek['name']}`")
            
        # Peek at your progress tracker table to see how it saves student_uid
        cursor.execute("SELECT DISTINCT student_uid FROM student_progress LIMIT 3")
        progress_peeks = cursor.fetchall()
        st.write("**Keys currently saved inside 'student_progress.student_uid' column:**")
        for p_row in progress_peeks:
            st.write(f"- `{p_row['student_uid']}`")
            
        conn.close()



    # ====================================================================
    # 🏫 SECTION A: PERSONALIZED STUDENT GRADEBOOK & PROGRESS METRICS
    # ====================================================================
    st.markdown(f"### 🏫 Personalized Learning Track Overview: {student_name} ({student_grade})")
    st.write("Below is your live active curriculum tracking matrix showing lesson milestones and quiz performance [INDEX].")
    
    personal_records = get_single_student_progress_metrics(student_uid)

    if not personal_records:
        # If they haven't submitted a quiz yet, give them a helpful hint with a shortcut button
        st.info("🎯 You haven't recorded any lesson progress metrics yet! Open your dashboard workspace to start your first assignment unit.")
        if st.button("🚀 Jump into Active Lesson Notes", type="primary", width="stretch"):
            st.session_state.current_page = "Main Chat"
            st.rerun()
    else:
        gradebook_list = []
        for record in personal_records:
            raw_lesson_id = record["lesson_id"]
            clean_lesson_title = str(raw_lesson_id).replace("_", " ").title() if raw_lesson_id else "General Topic"
            
            gradebook_list.append({
                "Curriculum Course Subject": record["subject"] or "General Study",
                "Assigned Unit Module": clean_lesson_title,
                "Current Learning Status": record["status"] or "Learning",
                "Highest Quiz Score": record["quiz_high_score"] if record["quiz_high_score"] is not None else 0,
                "Milestone Completed On": record["completed_at"] or "In Progress ⏳"
            })

        st.dataframe(
            gradebook_list,
            width="stretch",
            hide_index=True,
            column_config={
                "Highest Quiz Score": st.column_config.ProgressColumn(
                    "Top Mastery Performance",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                )
            }
        )

    st.write("##")
    st.write("---")
    st.write("##")

        # ====================================================================
    # 🏆 SECTION B: NATIONAL LEADERBOARD GRID (FIXED COLUMN FLOW)
    # ====================================================================
    st.markdown("### 🥇 National Leaderboard Rankings Selector")
    st.write("Select any academic grade level below to explore top master mind rankings.")
    
    # 🌟 LOCALIZED FILTER: This filter box now controls ONLY the bottom table ranking rows!
    default_grade_context = st.session_state.get("active_leaderboard_grade", student_grade)
    grade_options_list = [f"Grade {i}" for i in range(1, 13)]
    
    try:
        default_index = grade_options_list.index(default_grade_context)
    except ValueError:
        default_index = 5 
        
    selected_grade = st.selectbox(
        "🎯 Filter Leaderboard Standings by Level",
        options=grade_options_list,
        index=default_index,
        label_visibility="collapsed",
        key="leaderboard_grade_selector_dropdown"
    )

    st.write("##")
    st.markdown(f"#### 🏆 Current Top Standings for {selected_grade}")
    
    # Use your working database helper function safely
    leaderboard_records = get_grade_leaderboard(selected_grade, limit=100)

    if not leaderboard_records:
        st.info(f"No rank scores recorded for {selected_grade} students yet. Be the first to claim the top spot! 🌟")
    else:
        # 🌟 FIXED GRID: Enforce a clean 3-column layout row at all times
        podium_cols = st.columns(3, gap="medium")
        
        # 🥇 RENDER 1ST PLACE SLOT (Index 0)
        with podium_cols[0]:
            if len(leaderboard_records) > 0:
                record = leaderboard_records[0] # Selects the first student row dictionary safely
                st.markdown(f"""
<div style="background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); padding: 20px; border-radius: 16px; border: 2px solid #3b82f6; box-shadow: 0 0 20px rgba(59, 130, 246, 0.4); text-align: center; min-height: 160px;">
<h4 style='color:#60a5fa; margin:0; font-weight:700;'>🥇 1st Place</h4>
<h3 style='margin:12px 0 6px 0; color:#f8fafc; font-weight:800;'>{record['student_name']}</h3>
<p style='color:#94a3b8; font-size:13px; margin:0;'>🔥 Activities Completed: <b>{record['activity_count']}</b></p>
</div>
""", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color:#0f172a; border:1px dashed #1e293b; padding:20px; border-radius:16px; text-align:center; color:#64748b; min-height:160px;'><br>🥇 1st Place<br>Vacant</div>", unsafe_allow_html=True)

        # 🥈 RENDER 2ND PLACE SLOT (Index 1)
        with podium_cols[1]:
            if len(leaderboard_records) > 1:
                record = leaderboard_records[1] # Selects the second student row dictionary safely
                st.markdown(f"""
<div style="background-color: #0f172a; padding: 20px; border-radius: 16px; border: 1px solid #1e293b; text-align: center; min-height: 160px;">
<h4 style='color:#3b82f6; margin:0; font-weight:700;'>🥈 2nd Place</h4>
<h3 style='margin:12px 0 6px 0; color:#f8fafc; font-weight:800;'>{record['student_name']}</h3>
<p style='color:#94a3b8; font-size:13px; margin:0;'>🔥 Activities Completed: <b>{record['activity_count']}</b></p>
</div>
""", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color:#0f172a; border:1px dashed #1e293b; padding:20px; border-radius:16px; text-align:center; color:#64748b; min-height:160px;'><br>🥈 2nd Place<br>Waiting for Challenger ⚔️</div>", unsafe_allow_html=True)

        # 🥉 RENDER 3RD PLACE SLOT (Index 2)
        with podium_cols[2]:
            if len(leaderboard_records) > 2:
                record = leaderboard_records[2] # Selects the third student row dictionary safely
                st.markdown(f"""
<div style="background-color: #0f172a; padding: 20px; border-radius: 16px; border: 1px solid #1e293b; text-align: center; min-height: 160px;">
<h4 style='color:#3b82f6; margin:0; font-weight:700;'>🥉 3rd Place</h4>
<h3 style='margin:12px 0 6px 0; color:#f8fafc; font-weight:800;'>{record['student_name']}</h3>
<p style='color:#94a3b8; font-size:13px; margin:0;'>🔥 Activities Completed: <b>{record['activity_count']}</b></p>
</div>
""", unsafe_allow_html=True)
            else:
                st.markdown("<div style='background-color:#0f172a; border:1px dashed #1e293b; padding:20px; border-radius:16px; text-align:center; color:#64748b; min-height:160px;'><br>🥉 3rd Place<br>Waiting for Challenger ⚔️</div>", unsafe_allow_html=True)

        st.write("##")
        
        # Build full top 100 table registry roster list map
        leaderboard_list = []
        for rank_idx, record in enumerate(leaderboard_records):
            leaderboard_list.append({
                "Position Rank": f"#{rank_idx + 1}",
                "Learner Name": record["student_name"],
                "Course Milestones Completed": f"🎓 {record['activity_count']} Units",
                "Total Accumulation Score": f"🔥 {record['activity_count']} pts"
            })

        st.dataframe(
            leaderboard_list,
            width="stretch",
            hide_index=True,
            column_config={
                "Position Rank": st.column_config.TextColumn("Rank", width="small"),
                "Total Accumulation Score": st.column_config.TextColumn("Total Performance Score")
            }
        )
