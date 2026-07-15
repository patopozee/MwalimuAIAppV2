import streamlit as st
import base64
import fitz  # PyMuPDF for handling local PDF text parsing

class MwalimuVisionService:
    @staticmethod
    def process_chat_input_file(uploaded_file):
        if uploaded_file is None:
            return None
            
        try:
            # FIX: Properly extract the first file element out of the list container index [0]
            if isinstance(uploaded_file, list):
                if len(uploaded_file) == 0:
                    return None
                target_file = uploaded_file[0]  # 👈 CHANGED FROM uploaded_file TO uploaded_file[0]
            else:
                target_file = uploaded_file

            # Safely extract attributes from the isolated file object
            mime_type = str(target_file.type).lower()
            
            # 1. Handle PDF Documents using local text extraction
            if "pdf" in mime_type:
                file_bytes = target_file.getvalue()
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                
                extracted_text = ""
                for page in doc:
                    page_text = str(page.get_text())
                    extracted_text += page_text
                
                doc.close()
                
                return {
                    "type": "text_extraction",
                    "content": extracted_text,
                    "filename": str(target_file.name)
                }
                
            # 2. Handle standard learning material images
            else:
                file_bytes = target_file.getvalue()
                base64_data = base64.b64encode(file_bytes).decode("utf-8")
                
                return {
                    "type": "image_base64",
                    "mime_type": mime_type,
                    "content": f"data:{mime_type};base64,{base64_data}"
                }
                
        except Exception as e:
            st.error(f"Error extracting material contents: {e}")
            return None
