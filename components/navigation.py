import streamlit as st
from services.session_service import update_session

def render():
    st.sidebar.markdown("### Navigation Hub")

    # Map out display titles to their corresponding target properties
    links = [
        {"title": "🏠 Main Chat", "route": st.session_state.ROUTE_CHAT, "view": "main"},
        {"title": "🎙️ Voice Tutor", "route": st.session_state.ROUTE_VOICE, "view": "voice"},
        {"title": "⚡ AI Generators", "route": st.session_state.ROUTE_GENERATORS, "view": "generators"},
        {"title": "📚 Learning Dashboard", "route": st.session_state.ROUTE_LEARNING, "view": "learning"},
        {"title": "🏆 Leaderboard", "route": st.session_state.ROUTE_LEADERBOARD, "view": "leaderboard"}
    ]

    # Generate isolated tracking elements
    for link in links:
        # Check if this specific link matches what the user is currently looking at
        is_current = st.session_state.get("current_page") == link["title"]
        
        # Display a clean visual highlight if active, otherwise standard outline button
        btn_type = "primary" if is_current else "secondary"
        
        # Render clean, highly responsive navigation choices
        if st.sidebar.button(
            label=link["title"], 
            key=f"nav_btn_{link['view']}", 
            use_container_width=True,
            type=btn_type
        ):
            # Update state parameters globally
            st.session_state.current_page = link["title"]
            st.session_state.active_view = link["view"]
            
            # Sync selection change immediately into Firebase record entries
            update_session()
            
            # Force structural context swap rerender
            st.switch_page(link["route"])