import streamlit as st
import pypdf
import sqlite3
from services.database import (
    save_admin_material, 
    get_all_admin_materials, 
    delete_admin_material_by_id,
    DATABASE_NAME # Imported to run on-demand text recovery lookups safely
)
from config import CBC  # Assumes CBC holds your curriculum mappings

def render_admin_dashboard():
    # 🔙 Return Navigation Trigger Hook
    if st.button("⬅ Return to Student Dashboard", type="secondary"):
        st.session_state.current_page = "Main Chat"
        st.rerun()
        
    st.title("⚙️ Mwalimu AI - Admin Knowledge Base Manager")
    st.write("Upload reference textbooks, keys, or papers. The AI will strictly prioritize these when tutoring students.")
    
    # --- YOUR EXISTING UPLOAD MODULE CODE ---
    col1, col2, col3 = st.columns(3)
    with col1:
        subject = st.selectbox("Select Subject", list(CBC.keys()) if isinstance(CBC, dict) else ["Mathematics", "Science and Technology", "Social Studies"])
    with col2:
        topic = st.text_input("Topic Name (e.g., Whole Numbers)")
    with col3:
        sub_topic = st.text_input("Sub-Topic Name (e.g., Place Value)")
        
    uploaded_file = st.file_uploader("Upload reference documents (PDF or TXT)", type=["pdf", "txt"])
    
    if st.button("🚀 Publish Material Globally", use_container_width=True):
        if not subject or not topic or not uploaded_file:
            st.error("Please fill in Subject, Topic, and attach a valid file.")
            return
            
        file_text = ""
        file_type = uploaded_file.name.split(".")[-1].lower()
        
        with st.spinner("Processing document data..."):
            if file_type == "txt":
                file_text = uploaded_file.read().decode("utf-8")
            elif file_type == "pdf":
                pdf_reader = pypdf.PdfReader(uploaded_file)
                file_text = "\n".join([page.extract_text() for page in pdf_reader.pages])
                
        if file_text.strip():
            save_admin_material(subject, topic, sub_topic, uploaded_file.name, file_text)
            st.success(f"Successfully integrated '{uploaded_file.name}' into the {subject} AI memory base!")
            st.rerun()
        else:
            st.error("Could not extract legible text parameters from the uploaded file resource.")

    # ====================================================================    
        # ====================================================================
    # ⚠️ DEDICATED ADMIN DOCUMENT CLEARANCE CONFIRMATION DIALOG
    # ====================================================================
    @st.dialog("⚠️ Delete Reference Material")
    def confirm_delete_material_dialog(material_id, filename):
        st.write(f"Are you sure you want to permanently delete `{filename}` from Mwalimu's global brain memory? This action cannot be undone.")
        st.write("")
        
        col_yes, col_cancel = st.columns(2)
        with col_yes:
            if st.button("Yes, Purge Permanently", use_container_width=True, type="primary"):
                with st.spinner("Purging reference files..."):
                    # Drop row instantly out of the SQLite tables database tracks
                    delete_admin_material_by_id(material_id)
                    st.toast(f"Removed '{filename}' successfully!", icon="🗑️")
                    st.rerun()
                    
        with col_cancel:
            if st.button("Cancel", use_container_width=True):
                st.rerun()

    # ====================================================================
    # 📚 DYNAMIC CONTENT TRACKER TABLE VIEW (PLACED NEATLY AT THE FOOTER)
    # ====================================================================
    st.write("---")
    st.subheader("📋 Active Global Knowledge Base Overview")
    st.write("Below are the curriculum reference files currently loaded into Mwalimu's brain memory track database.")

    # Pull active database rows directly
    materials_list = get_all_admin_materials()

    if not materials_list:
        st.info("No global reference materials uploaded yet. Use the upload module form above to add your first classroom chapter document!")
        return

    # Render each document inside a clean structural list card layout
    for document_item in materials_list:
        with st.container(border=True):
            info_column, action_column = st.columns([3, 1], vertical_alignment="center")
            
            with info_column:
                st.markdown(f"📄 **File Asset:** `{document_item['filename']}`")
                
                # Format an elegant metadata profile label tracking row mapping curriculum strings
                sub_topic_label = document_item['sub_topic'] if document_item['sub_topic'] else "General Context"
                st.caption(
                    f"📚 **Subject:** {document_item['subject']} | "
                    f"🎯 **Topic Framework:** {document_item['topic']} ({sub_topic_label}) \n\n"
                    f"📅 **Published on:** {document_item['uploaded_at']}"
                )
  
            with action_column:
                # Create mini inline side-by-side button slots inside the action block
                btn_col1, btn_col2 = st.columns(2)
                #=====
                with btn_col1:
                    # Safe IDM Fix: Regular button toggles user download intent state
                    prepare_key = f"prep_dl_{document_item['id']}"
                    trigger_download = st.button("📥 Download", key=prepare_key, use_container_width=True)
                    
                    if trigger_download:
                        raw_file_content = document_item["content"] if document_item["content"] else ""
                        
                        # ==========================================================
                        # 🚀 REAL-TIME TEXT-TO-PDF GENERATION CORE ENGINE
                        # ==========================================================
                        import io
                        from reportlab.lib.pagesizes import letter
                        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                        
                        # Create an in-memory binary stream byte wrapper buffer
                        pdf_buffer = io.BytesIO()
                        
                        # Initialize layout document sheet geometry sizes
                        doc = SimpleDocTemplate(
                            pdf_buffer, 
                            pagesize=letter,
                            rightMargin=54, leftMargin=54, 
                            topMargin=54, bottomMargin=54
                        )
                        
                        # Configure clean cascading visual text style sheets
                        styles = getSampleStyleSheet()
                        body_style = ParagraphStyle(
                            'PDFBodyStyle',
                            parent=styles['Normal'],
                            fontName='Helvetica',
                            fontSize=10,
                            leading=14, # Controls line height spacing to look readable
                            spaceAfter=6
                        )
                        
                        story = []
                        
                        # Add a bold title heading layout to your backup document tracking sheet
                        title_style = ParagraphStyle(
                            'PDFTitleStyle',
                            parent=styles['Heading1'],
                            fontName='Helvetica-Bold',
                            fontSize=16,
                            leading=20,
                            spaceAfter=15
                        )
                        story.append(Paragraph(f"Backup Resource: {document_item['filename']}", title_style))
                        story.append(Spacer(1, 10))
                        
                        # Process raw text contents line by line into individual wrapped paragraphs
                        raw_lines = raw_file_content.split('\n')
                        for line in raw_lines:
                            line_stripped = line.strip()
                            if line_stripped:
                                # Escape basic HTML entity markers to prevent reportlab engine syntax errors
                                clean_line = line_stripped.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                                story.append(Paragraph(clean_line, body_style))
                            else:
                                # Replicate layout line gaps safely
                                story.append(Spacer(1, 8))
                                
                        # Build the compiled visual structure directly into our memory bytes stream
                        doc.build(story)
                        pdf_data_bytes = pdf_buffer.getvalue()
                        pdf_buffer.close()
                        # ==========================================================
                        
                        # Clean up the output download file name tag
                        clean_filename = document_item['filename']
                        if clean_filename.lower().endswith(".pdf"):
                            clean_filename = clean_filename[:-4]
                        elif clean_filename.lower().endswith(".txt"):
                            clean_filename = clean_filename[:-4]
                        
                        # Triggers a native structured PDF file delivery to your browser canvas
                        st.download_button(
                            label="⚡ Click to Save PDF",
                            data=pdf_data_bytes,
                            file_name=f"backup_{clean_filename}.pdf", # Saves as a genuine PDF
                            mime="application/pdf", # Hardlocked to structured binary content types
                            key=f"real_dl_{document_item['id']}",
                            use_container_width=True
                        )


                
                with btn_col2:
                    # Triggers the newly integrated confirmation popup overlay seamlessly
                    button_unique_id = f"delete_doc_asset_id_{document_item['id']}"
                    if st.button("🗑️ Delete", key=button_unique_id, use_container_width=True, type="secondary"):
                        confirm_delete_material_dialog(document_item['id'], document_item['filename'])
