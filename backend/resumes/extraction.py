import io
from pathlib import Path
from typing import Optional

from docx import Document
import fitz  # PyMuPDF

# OCR imports - optional, gracefully handled if not available
try:
    import pytesseract
    from PIL import Image
    import os
    import shutil
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Configure pytesseract to find Tesseract executable
    # Try standard Windows location first, then system PATH
    
    # Standard Windows installation path
    TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # Check if we can find Tesseract in standard location or PATH
    if os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        logger.debug(f"Set tesseract_cmd to: {TESSERACT_CMD}")
    elif shutil.which("tesseract"):
        tesseract_path = shutil.which("tesseract")
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        logger.debug(f"Found tesseract in PATH: {tesseract_path}")
    
    # Verify Tesseract is actually accessible
    HAS_OCR = False
    OCR_ERROR_REASON = ""
    try:
        # Test actual accessibility
        version = pytesseract.get_tesseract_version()
        HAS_OCR = True
        logger.info(f"Tesseract OCR available: version {version}")
    except pytesseract.TesseractNotFoundError as e:
        OCR_ERROR_REASON = f"Tesseract executable not found: {e}"
        logger.warning(OCR_ERROR_REASON)
    except Exception as e:
        OCR_ERROR_REASON = f"Tesseract verification failed: {e}"
        logger.warning(OCR_ERROR_REASON)
except ImportError as e:
    HAS_OCR = False
    OCR_ERROR_REASON = f"pytesseract/PIL not installed: {e}"


def extract_text_from_pdf(uploaded_file) -> str:
    """
    Ekstrak teks dari PDF menggunakan PyMuPDF.
    Jika PDF berisi gambar (scan/hasil pindai), gunakan Tesseract OCR sebagai fallback.
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Returns:
        str: Teks hasil ekstraksi
        
    Raises:
        ValueError: Jika PDF tidak dapat dibuka, rusak, atau teks kosong tanpa OCR fallback
    """
    uploaded_file.seek(0)
    
    try:
        # Buka PDF dengan PyMuPDF
        pdf_stream = io.BytesIO(uploaded_file.read())
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        # Ekstrak teks dari setiap halaman
        text_parts = []
        for page_num, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        
        doc.close()
        extracted_text = "\n".join(text_parts).strip()
        
        # Jika tidak ada teks, coba OCR pada gambar
        if not extracted_text:
            if HAS_OCR:
                extracted_text = _extract_text_with_ocr(uploaded_file)
            else:
                raise ValueError(
                    "Teks tidak ditemukan di PDF. PDF hasil scan memerlukan Tesseract OCR, "
                    "tetapi pytesseract tidak tersedia. "
                    "Silakan instal pytesseract dan Tesseract executable."
                )
        
        return extracted_text
    
    except (fitz.FileDataError, fitz.EmptyFileError, RuntimeError) as e:
        # FileDataError: PDF rusak atau tidak dapat dibuka
        # EmptyFileError: PDF kosong
        # RuntimeError: Lainnya dari PyMuPDF 1.23.8
        error_msg = str(e).lower()
        if "encrypt" in error_msg or "permission" in error_msg:
            raise ValueError("PDF terenkripsi tidak didukung.")
        else:
            raise ValueError(f"File PDF rusak atau tidak dapat dibuka: {str(e)}")
    except Exception as e:
        raise ValueError(f"Gagal memproses PDF: {str(e)}")
    finally:
        uploaded_file.seek(0)


def _extract_text_with_ocr(uploaded_file) -> str:
    """
    Ekstrak teks dari PDF menggunakan Tesseract OCR.
    Render halaman PDF menjadi gambar dan proses dengan OCR.
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Returns:
        str: Teks hasil OCR
        
    Raises:
        ValueError: Jika OCR gagal atau executable tidak tersedia
    """
    if not HAS_OCR:
        raise ValueError(
            "pytesseract dan PIL tidak tersedia. "
            "Silakan instal: pip install pytesseract pillow"
        )
    
    uploaded_file.seek(0)
    
    try:
        pdf_stream = io.BytesIO(uploaded_file.read())
        doc = fitz.open(stream=pdf_stream, filetype="pdf")
        
        ocr_results = []
        for page_num, page in enumerate(doc):
            # Render halaman menjadi gambar dengan resolusi 150 DPI (cukup untuk OCR)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image_data = pix.tobytes(output="ppm")
            image = Image.open(io.BytesIO(image_data))
            
            # Jalankan OCR - coba bahasa Indonesia dulu, fallback ke Inggris
            try:
                text = pytesseract.image_to_string(image, lang="ind")
            except pytesseract.TesseractNotFoundError:
                raise ValueError(
                    "Tesseract executable tidak ditemukan. "
                    "Instal Tesseract dari https://github.com/UB-Mannheim/tesseract/wiki"
                )
            except Exception:
                # Fallback ke Inggris jika paket bahasa Indonesia tidak tersedia
                text = pytesseract.image_to_string(image, lang="eng")
            
            if text.strip():
                ocr_results.append(text)
        
        doc.close()
        
        extracted_text = "\n".join(ocr_results).strip()
        
        if not extracted_text:
            raise ValueError(
                "OCR tidak menghasilkan teks. PDF mungkin gambar berkualitas rendah atau tidak mengandung teks yang dapat dikenali."
            )
        
        return extracted_text
    
    except pytesseract.TesseractNotFoundError:
        raise ValueError(
            "Tesseract OCR executable tidak ditemukan di sistem. "
            "Instal dari: https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as e:
        raise ValueError(f"Gagal memproses OCR: {str(e)}")
    finally:
        uploaded_file.seek(0)


def extract_text_from_docx(uploaded_file) -> str:
    """
    Ekstrak teks dari DOCX.
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Returns:
        str: Teks hasil ekstraksi
        
    Raises:
        ValueError: Jika DOCX tidak dapat dibuka atau tidak ada teks
    """
    uploaded_file.seek(0)
    
    try:
        document = Document(uploaded_file)
        
        # Ekstrak dari paragraf
        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        extracted_text = "\n".join(paragraphs)
        
        # Ekstrak dari tabel
        for table in document.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells
                )
                if row_text.strip(" |"):
                    extracted_text += "\n" + row_text
        
        return extracted_text.strip()
    
    except Exception as e:
        raise ValueError(f"Gagal memproses DOCX: {str(e)}")
    finally:
        uploaded_file.seek(0)


def extract_text_from_file(uploaded_file) -> str:
    """
    Ekstrak teks dari file PDF atau DOCX.
    
    Untuk PDF:
    - Menggunakan PyMuPDF untuk ekstraksi teks digital
    - Jika tidak ada teks, fallback ke Tesseract OCR untuk PDF scan
    
    Untuk DOCX:
    - Menggunakan python-docx
    
    Args:
        uploaded_file: Django UploadedFile object
        
    Returns:
        str: Teks hasil ekstraksi (sudah distrip)
        
    Raises:
        ValueError: Untuk berbagai kondisi kesalahan
    """
    extension = Path(uploaded_file.name).suffix.lower()
    
    if extension == ".pdf":
        extracted_text = extract_text_from_pdf(uploaded_file)
    elif extension == ".docx":
        extracted_text = extract_text_from_docx(uploaded_file)
    else:
        raise ValueError("Format file harus PDF atau DOCX.")
    
    if not extracted_text.strip():
        raise ValueError(
            "Teks tidak ditemukan dalam file. "
            "Pastikan file mengandung teks yang dapat dibaca."
        )
    
    return extracted_text.strip()
