"""
doc_parser.py
Extracts text from an uploaded PDF (policy, vendor questionnaire, etc.)
so it can be handed to the AI layer for evidence-gap analysis.
"""

import io


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF given as raw bytes (e.g. from a Streamlit
    file_uploader). Returns a single string with page breaks marked.
    """
    try:
        import pdfplumber
    except ImportError as e:
        raise ImportError(
            "pdfplumber is required for PDF parsing. Install with: "
            "pip install pdfplumber"
        ) from e

    text_chunks = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            text_chunks.append(f"--- Page {i + 1} ---\n{page_text}")

    return "\n\n".join(text_chunks).strip()


def truncate_for_prompt(text: str, max_chars: int = 8000) -> str:
    """
    Keep prompt payloads bounded. Simple head-truncation is fine for an
    MVP; swap for chunking + summarization if documents get large.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[...truncated...]"
