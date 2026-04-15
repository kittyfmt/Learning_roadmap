from PyPDF2 import PdfReader

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from a Streamlit UploadedFile object."""
    if uploaded_file is None:
        return ""
    
    reader = PdfReader(uploaded_file)
    text = ""
    
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
            
    return text.strip()