import streamlit as st

from services.database import (
    clear_student_chat_history,
    get_ask_mwalimu_history,
    get_student_stats,
)


def render():

    current_subject = st.session_state.get(
        "active_subject",
        "General Studies",
    )

    # Material shortcode injected directly into the dialog title string
    @st.dialog(f":material/delete: Clear {current_subject} Chat")
    def confirm_clear_chat():

        st.markdown(
            f"""
    ### Delete **{current_subject}** Chat History

    This will permanently delete all conversations for **{current_subject}**.

    Other subjects remain untouched.

    :material/warning: This cannot be undone.
    """
        )

        col1, col2 = st.columns(2)

        with col1:

            # Native button using the built-in offline delete symbol
            if st.button(
                label="Delete History",
                icon=":material/delete:",
                type="primary",
                use_container_width=True,
            ):

                clear_student_chat_history(
                    student_uid=str(st.session_state.get("uid", "")),
                    grade=st.session_state.get("grade", "Grade 6"),
                    age=int(st.session_state.get("age", 12)),
                    subject=current_subject,
                )

                st.session_state.ask_mwalimu_history = []

                if hasattr(get_ask_mwalimu_history, "clear"):
                    get_ask_mwalimu_history.clear()

                if hasattr(get_student_stats, "clear"):
                    get_student_stats.clear()

                # Native toast notification displaying local icon framework
                st.toast(
                    f"{current_subject} history deleted.",
                    icon=":material/delete:",
                )

                st.rerun()

        with col2:

            if st.button(
                "Cancel",
                use_container_width=True,
            ):
                st.rerun()

    # -------------------------
    # Sidebar
    # -------------------------

    st.sidebar.markdown("---")

    with st.sidebar.container(border=True):

        # Injected local icon inside heading markdown
        st.markdown("### :material/chat: Chat")

        # Native trigger button updated to use internal asset assets
        if st.button(
            label="Clear Chat History",
            icon=":material/delete_sweep:",
            use_container_width=True,
        ):
            confirm_clear_chat()
