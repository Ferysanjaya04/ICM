
from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text_from_file(uploaded_file):
    """
    Mengekstrak teks dari PDF atau DOCX.
    Mengembalikan teks sebagai string.
    """
    extension = Path(uploaded_file.name).suffix.lower()

    uploaded_file.seek(0)

    if extension == ".pdf":
        reader = PdfReader(uploaded_file)

        if reader.is_encrypted:
            raise ValueError("PDF terenkripsi tidak didukung.")

        text_parts = [
            page.extract_text() or ""
            for page in reader.pages
        ]
        extracted_text = "\n".join(text_parts)

    elif extension == ".docx":
        document = Document(uploaded_file)

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        extracted_text = "\n".join(paragraphs)

        for table in document.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells
                )
                if row_text.strip(" |"):
                    extracted_text += "\n" + row_text

    else:
        raise ValueError("Format file harus PDF atau DOCX.")

    uploaded_file.seek(0)

    if not extracted_text.strip():
        raise ValueError(
            "Teks tidak ditemukan. PDF hasil scan mungkin memerlukan OCR."
        )

    return extracted_text.strip()
