import streamlit as st


def render():

    name = st.session_state.get("student_name", "Student")
    grade = st.session_state.get("student_grade", "Grade 6")
    tier = st.session_state.get("subscription_tier", "FREE")
    progress = st.session_state.get("overall_progress", 0)

    avatar = name[:1].upper()

    st.sidebar.markdown("---")

    st.sidebar.markdown("### Student Profile")
    with st.sidebar.expander("📝 Student Information", expanded=False):
        name = str(st.session_state.get("student_name") or "Student").strip().title()
        grade = st.session_state.get("grade", "Grade 1")
        age = int(st.session_state.get("age", 10))
        favorite_subject = st.text_input(
                    "Favorite Subject",
                    value=st.session_state.get("favorite_subject") or ""
                )
        weak_subject = st.text_input(
                    "Needs Improvement",
                    value=st.session_state.get("weak_subject") or ""
                )
        initial = name[:1].upper() if name else "S"
        st.sidebar.markdown(
                f"""
            <div class="profile-card">

            <div class="profile-avatar">
            {initial}
            </div>

            <div class="profile-name">
            {name}
            </div>

            <div class="profile-grade">
            🎓 {grade}
            </div>

            <hr style="opacity:.12;">

            <div style="font-size:14px;line-height:1.8;">

            🎂 <b>Age</b> : {age}<br>

            ⭐ <b>Favorite</b> : {favorite_subject or "Not Set"}<br>

            📉 <b>Needs Help</b> : {weak_subject or "Not Set"}

            </div>
            """,
            unsafe_allow_html=True
            )
   

    st.sidebar.progress(progress / 100)

    st.sidebar.caption(f"{progress}% learning progress")

    if st.sidebar.button(
        "⚙️ Edit Profile",
        
        key="profile_btn",
        use_container_width=True,
    ):
        st.switch_page(st.session_state.ROUTE_EDIT_PROFILE)