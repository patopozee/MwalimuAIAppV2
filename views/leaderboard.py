import streamlit as st

def render(): 

    from ui_components.leaderboard_page import render_student_leaderboard_page
    render_student_leaderboard_page()  