import streamlit as st
import sqlite3
from services.database import DATABASE_NAME, get_grade_leaderboard
from services.navigation_service import navigate_to

def get_single_student_progress_metrics(student_id_or_uid):
    """Fetches a detailed curriculum progress ledger specifically for the logged-in student profile."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Keep this targeting the student_progress table to render their personal gradebook row matrix
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
    # with st.expander("🕵️‍♂️ Database Key Alignment Debugger (Click to Expand)"):
    #     st.write(f"**Active Session UID String:** `{student_uid}`")
        
    #     # Pull raw rows straight out of your database to see exactly what keys look like
    #     conn = sqlite3.connect(DATABASE_NAME)
    #     conn.row_factory = sqlite3.Row
    #     cursor = conn.cursor()
        
    #     # Peek at the last registered student row
    #     cursor.execute("SELECT id, name FROM students ORDER BY id DESC LIMIT 1")
    #     student_peek = cursor.fetchone()
    #     if student_peek:
    #         st.write(f"**Last Registered Student in DB:** ID/UID Field = `{student_peek['id']}` | Name = `{student_peek['name']}`")
            
    #     # Peek at your progress tracker table to see how it saves student_uid
    #     cursor.execute("SELECT DISTINCT student_uid FROM student_progress LIMIT 3")
    #     progress_peeks = cursor.fetchall()
    #     st.write("**Keys currently saved inside 'student_progress.student_uid' column:**")
    #     for p_row in progress_peeks:
    #         st.write(f"- `{p_row['student_uid']}`")
            
    #     conn.close()



    # ====================================================================
    # 🏫 SECTION A: PERSONALIZED STUDENT GRADEBOOK & PROGRESS METRICS
    # ====================================================================
    podium_svg_base = "style='width:24px; height:24px; vertical-align:middle; margin-right:4px; fill:{color};'"
    svg_trophy = "<svg xmlns='http://w3.org' viewBox='0 -960 960 960' {style}><path d='M280-120v-80h160v-124q-49-11-87.5-41.5T296-440H160q-33 0-56.5-23.5T80-520v-120q0-33 23.5-56.5T160-720h120v-40q0-33 23.5-56.5T360-840h240q33 0 56.5 23.5T680-720v40h120q33 0 56.5 23.5T880-640v120q0 33-23.5 56.5T800-440H664q-17 44-55.5 74.5T520-324v124h160v80H280Zm0-400H160v120h120v-120Zm400 0v120h120v-120H680Zm-320-80h240v-160H360v160Zm120 240q50 0 85-35t35-85v-40H320v40q0 50 35 85t85 35Zm0-120Z'/></svg>"

    # ====================================================================
    # 🏫 SECTION A: PERSONALIZED STUDENT GRADEBOOK & PROGRESS METRICS
    # ====================================================================
    st.markdown(f"### :material/school: Personalized Learning Track Overview: {student_name} ({student_grade})")
    st.write("Below is your live active curriculum tracking matrix showing lesson milestones and quiz performance.")

    personal_records = get_single_student_progress_metrics(student_uid)

    if not personal_records:
        # Swapped target emoji out for native local icon string
        st.info("You haven't recorded any lesson progress metrics yet! Open your dashboard workspace to start your first assignment unit.", icon=":material/ads_click:")
        if st.button("Jump into Active Lesson Notes", icon=":material/rocket_launch:", type="primary", width='stretch'):
            navigate_to(
                st.session_state.ROUTE_LEARNING,
                "Learning Dashboard",
                "learning",
            )
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
                # Swapped hourglass text emoji with clear explicit string subtext
                "Milestone Completed On": record["completed_at"] or "In Progress"
            })

        st.dataframe(
            gradebook_list,
            width='stretch',
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
    st.markdown("### :material/workspace_premium: National Leaderboard Rankings Selector")
    st.write("Select any academic grade level below to explore top master mind rankings.")

    default_grade_context = st.session_state.get("active_leaderboard_grade", student_grade)
    grade_options_list = [f"Grade {i}" for i in range(1, 13)]

    try:
        default_index = grade_options_list.index(default_grade_context)
    except ValueError:
        default_index = 5 
        
    selected_grade = st.selectbox(
        "Filter Leaderboard Standings by Level",
        options=grade_options_list,
        index=default_index,
        label_visibility="collapsed",
        key="leaderboard_grade_selector_dropdown"
    )

    st.write("##")
    st.markdown(f"#### Current Top Standings for {selected_grade}")

    st.cache_data.clear()

    try:
        conn = sqlite3.connect(DATABASE_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT student_name, score, count(id) as activity_count, sum(score) as total_score, student_grade
            FROM leaderboard 
            WHERE student_grade = ? 
            GROUP BY student_uid
            ORDER BY score DESC 
            LIMIT 100
        """, (selected_grade,))
        raw_leaderboard_records = cursor.fetchall()
        conn.close()
    except sqlite3.OperationalError:
        raw_leaderboard_records = []

    if not raw_leaderboard_records:
        st.info(f"No rank scores recorded for {selected_grade} students yet. Be the first to claim the top spot!")
    else:
        leaderboard_records = [dict(row) for row in raw_leaderboard_records]

        # Enforced Grid Structure
        podium_cols = st.columns(3, gap="medium")
        
        # 🥇 1ST PLACE CONTAINER (Gold Vector SVG Icon Inline Implementation)
        with podium_cols[0]:
            if len(leaderboard_records) > 0:
                record = leaderboard_records[0]
                svg_gold = svg_trophy.format(style=podium_svg_base.format(color="#FACC15"))
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%); padding: 20px; border-radius: 16px; border: 2px solid #3b82f6; box-shadow: 0 0 20px rgba(59, 130, 246, 0.4); text-align: center; min-height: 160px;">
                    <h4 style='color:#FACC15; margin:0; font-weight:700; display:flex; align-items:center; justify-content:center;'>{svg_gold} <span>1st Place</span></h4>
                    <h3 style='margin:12px 0 6px 0; color:#f8fafc; font-weight:800;'>{record['student_name']}</h3>
                    <p style='color:#94a3b8; font-size:13px; margin:0;'>Activities Completed: <b>{record['activity_count']}</b></p>
                </div>
                """, unsafe_allow_html=True)

        # 🥈 2ND PLACE CONTAINER (Silver Vector SVG Icon Inline Implementation)
        with podium_cols[1]:
            if len(leaderboard_records) > 1:
                record = leaderboard_records[1]
                svg_silver = svg_trophy.format(style=podium_svg_base.format(color="#94A3B8"))
                st.markdown(f"""
                <div style="background-color: #0f172a; padding: 20px; border-radius: 16px; border: 1px solid #1e293b; text-align: center; min-height: 160px;">
                    <h4 style='color:#94A3B8; margin:0; font-weight:700; display:flex; align-items:center; justify-content:center;'>{svg_silver} <span>2nd Place</span></h4>
                    <h3 style='margin:12px 0 6px 0; color:#f8fafc; font-weight:800;'>{record['student_name']}</h3>
                    <p style='color:#94a3b8; font-size:13px; margin:0;'>Activities Completed: <b>{record['activity_count']}</b></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                svg_silver = svg_trophy.format(style=podium_svg_base.format(color="#475569"))
                st.markdown(f"""
                <div style='background-color:#0f172a; border:1px dashed #1e293b; padding:20px; border-radius:16px; text-align:center; color:#64748b; min-height:160px; display:flex; flex-direction:column; align-items:center; justify-content:center;'>
                    <div>{svg_silver} 2nd Place</div>
                    <div style='font-size:12px; margin-top:4px;'>Waiting for Challenger</div>
                </div>
                """, unsafe_allow_html=True)

        # 🥉 3RD PLACE CONTAINER (Bronze Vector SVG Icon Inline Implementation)
        with podium_cols[2]:
            if len(leaderboard_records) > 2:
                record = leaderboard_records[2]
                svg_bronze = svg_trophy.format(style=podium_svg_base.format(color="#CD7F32"))
                st.markdown(f"""
                <div style="background-color: #0f172a; padding: 20px; border-radius: 16px; border: 1px solid #1e293b; text-align: center; min-height: 160px;">
                    <h4 style='color:#CD7F32; margin:0; font-weight:700; display:flex; align-items:center; justify-content:center;'>{svg_bronze} <span>3rd Place</span></h4>
                    <h3 style='margin:12px 0 6px 0; color:#f8fafc; font-weight:800;'>{record['student_name']}</h3>
                    <p style='color:#94a3b8; font-size:13px; margin:0;'>Activities Completed: <b>{record['activity_count']}</b></p>
                </div>
                """, unsafe_allow_html=True)
            else:
                svg_bronze = svg_trophy.format(style=podium_svg_base.format(color="#475569"))
                st.markdown(f"""
                <div style='background-color:#0f172a; border:1px dashed #1e293b; padding:20px; border-radius:16px; text-align:center; color:#64748b; min-height:160px; display:flex; flex-direction:column; align-items:center; justify-content:center;'>
                    <div>{svg_bronze} 3rd Place</div>
                    <div style='font-size:12px; margin-top:4px;'>Waiting for Challenger</div>
                </div>
                """, unsafe_allow_html=True)

        st.write("##")
        
        # 📋 CORRECTED INTEGRATION REGISTRY TABLE
        leaderboard_list = []
        for rank_idx, record in enumerate(leaderboard_records):
            leaderboard_list.append({
                "Position Rank": f"#{rank_idx + 1}",
                "Learner Name": record["student_name"],
                "Course Milestones Completed": f"{record['activity_count']} Units",
                "Total Accumulation Score": f"{record['total_score']} pts"
            })

        st.dataframe(
            leaderboard_list,
            width='stretch',
            hide_index=True,
            column_config={
                "Position Rank": st.column_config.TextColumn("Rank"),
                "Total Accumulation Score": st.column_config.TextColumn("Total Performance Score")
            }
        )