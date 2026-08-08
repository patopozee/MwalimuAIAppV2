import streamlit as st
from components.loaders import show_page_loader


def render(): 
    # 1. INSTANT UI FEEDBACK: Mount loader slot immediately onto screen
    loader_slot = st.empty()
    with loader_slot.container():
        show_page_loader("Fetching national leaderboard rankings...")

    # 2. LAZY IMPORT & HEAVY DATA FETCHING
    from ui_components.leaderboard_page import render_student_leaderboard_page
    
    # 3. CLEAR LOADER: Remove loader slot right before rendering rankings
    loader_slot.empty()

    # 4. RENDER PAGE
    render_student_leaderboard_page()  