"""
printing/validators.py
======================
Server-side file validation, security inspection, and page count detection.

Why this is needed:
1. Attackers can rename dangerous executable files (e.g. .exe to .pdf).
   We inspect file extensions, size limits, and initial file signature bytes (magic headers).
2. We detect actual printable page count for accurate price calculation:
   - PDFs: Inspected using pure-Python pypdf.
   - Images (.jpg, .png): Standard single-page documents.
   - Word (.docx): Inspected via python-docx paragraph/page estimate or 1 page fallback.
   - Word (.doc legacy): Safely noted; conversion recommended.
"""

import os
from io import BytesIO
from django.conf import settings
from django.core.exceptions import ValidationError


# Magic byte signatures for supported file formats
FILE_SIGNATURES = {
    'pdf': [b'%PDF-'],
    'png': [b'\x89PNG\r\n\x1a\n'],
    'jpg': [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'docx': [b'PK\x03\x04'],  # ZIP container header
    'doc': [b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'],  # OLE Compound Document
}


def validate_uploaded_document(uploaded_file):
    """
    Validates file extension, maximum file size, and file signature.
    Raises ValidationError if any check fails.
    Returns: detected_type ('PDF', 'DOCX', 'DOC', 'IMAGE')
    """
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower().lstrip('.')

    # 1. Extension check
    if f".{ext}" not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_DOCUMENT_EXTENSIONS)
        raise ValidationError(
            f"Unsupported file format '.{ext}'. Supported formats are: {allowed}"
        )

    # 2. File size check
    max_bytes = getattr(settings, 'MAX_UPLOAD_SIZE_BYTES', 15 * 1024 * 1024)
    max_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 15)
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            f"File size ({uploaded_file.size / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of {max_mb} MB."
        )

    if uploaded_file.size == 0:
        raise ValidationError("The uploaded file is empty (0 bytes). Please upload a valid document.")

    # 3. Magic signature verification
    # Read first 32 bytes to inspect magic numbers
    uploaded_file.seek(0)
    header = uploaded_file.read(32)
    uploaded_file.seek(0)  # Reset pointer back to beginning

    expected_signatures = FILE_SIGNATURES.get(ext, [])
    if expected_signatures:
        matched = any(header.startswith(sig) for sig in expected_signatures)
        if not matched:
            raise ValidationError(
                f"File content does not match the '{ext}' extension. Upload a genuine, uncorrupted document."
            )

    # 4. Map to Document model file_type
    if ext == 'pdf':
        return 'PDF'
    elif ext == 'docx':
        return 'DOCX'
    elif ext == 'doc':
        return 'DOC'
    elif ext in ['jpg', 'jpeg', 'png']:
        return 'IMAGE'
    return 'PDF'


def detect_document_page_count(uploaded_file, file_type: str) -> tuple[int, str]:
    """
    Safely determines the printable page count of the file.
    Returns a tuple: (page_count, status)
    where status is 'DETECTED', 'DEFAULT', or 'ESTIMATED'.
    """
    if file_type == 'IMAGE':
        return 1, 'DETECTED'

    if file_type == 'PDF':
        try:
            import pypdf
            uploaded_file.seek(0)
            reader = pypdf.PdfReader(uploaded_file)
            page_count = len(reader.pages)
            uploaded_file.seek(0)
            if page_count > 0:
                return page_count, 'DETECTED'
        except Exception:
            # Fallback if PDF has unusual encryption or minor corruption
            uploaded_file.seek(0)
            return 1, 'DEFAULT'

    if file_type == 'DOCX':
        try:
            import docx
            uploaded_file.seek(0)
            doc = docx.Document(uploaded_file)
            uploaded_file.seek(0)
            # Rough estimate for docx based on paragraph count (~6-8 paragraphs per page)
            paragraphs = [p for p in doc.paragraphs if p.text.strip()]
            est_pages = max(1, len(paragraphs) // 7 + (1 if len(paragraphs) % 7 else 0))
            return est_pages, 'ESTIMATED'
        except Exception:
            uploaded_file.seek(0)
            return 1, 'DEFAULT'

    if file_type == 'DOC':
        # Legacy binary Word doc cannot be safely page-counted in pure Python
        return 1, 'DEFAULT'

    return 1, 'DEFAULT'
