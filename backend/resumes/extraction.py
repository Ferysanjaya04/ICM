
"""
ICM - Resume Document Extraction

Mendukung:
- PDF digital menggunakan PyMuPDF
- PDF hasil scan menggunakan Tesseract OCR
- PDF campuran teks digital dan halaman scan
- DOCX dengan paragraf dan tabel sesuai urutan dokumen
- Normalisasi teks
- Validasi dan pembatasan sumber daya

Fungsi utama:
    extract_text_from_file(uploaded_file)

Kompatibilitas:
    extract_text_from_pdf(uploaded_file)
    extract_text_from_docx(uploaded_file)
    _extract_text_with_ocr(uploaded_file)
    HAS_OCR
    OCR_ERROR_REASON
"""

import io
import time
import logging
import os
import re
import shutil
import zipfile
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    import fitz

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_FILE_BYTES = 10 * 1024 * 1024

MAX_PDF_PAGES = 30
MAX_OCR_PAGES = 12
MAX_OCR_PIXELS = 16_000_000

MAX_DOCX_UNCOMPRESSED_BYTES = 60 * 1024 * 1024
MAX_DOCX_ENTRIES = 2000

OCR_DPI = 180
OCR_TIMEOUT = 20
MAX_OCR_TOTAL_SECONDS = 60

MIN_PAGE_TEXT_CHARS = 60

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


# ============================================================
# OCR AVAILABILITY
# ============================================================

try:
    import pytesseract
except ImportError:
    pytesseract = None


def _get_tesseract():
    """
    Temukan executable Tesseract.

    Prioritas:
    1. Environment variable TESSERACT_CMD
    2. Tesseract pada system PATH
    3. Lokasi instalasi standar Windows

    Return:
        modul pytesseract atau None.
    """

    if pytesseract is None:
        return None

    executable = os.getenv("TESSERACT_CMD")

    if executable:
        executable = executable.strip('"').strip("'")

        if not (
            os.path.isfile(executable)
            or shutil.which(executable)
        ):
            logger.warning(
                "TESSERACT_CMD tidak menunjuk executable valid."
            )
            return None

    else:
        executable = shutil.which("tesseract")

        if not executable and os.name == "nt":
            windows_path = (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )

            if os.path.isfile(windows_path):
                executable = windows_path

    if not executable:
        return None

    pytesseract.pytesseract.tesseract_cmd = executable

    return pytesseract


def _check_ocr_availability():
    """
    Mengecek apakah OCR benar-benar dapat dijalankan.

    Hasil:
        (available: bool, reason: str)
    """

    tesseract = _get_tesseract()

    if tesseract is None:
        return (
            False,
            "pytesseract atau executable Tesseract tidak tersedia.",
        )

    try:
        from PIL import Image  # noqa: F401

        tesseract.get_tesseract_version()

        return True, ""

    except Exception as exc:
        logger.warning(
            "OCR initialization failed: %s",
            type(exc).__name__,
        )

        return (
            False,
            "Tesseract atau dependensi OCR tidak dapat dijalankan.",
        )


# Variabel kompatibilitas untuk tests_ocr.py
HAS_OCR, OCR_ERROR_REASON = _check_ocr_availability()


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def _normalize_text(text: str) -> str:
    """
    Normalisasi teks tanpa menghilangkan pemisah baris.

    Tidak melakukan:
    - Penghapusan keyword teknis
    - Pengubahan huruf menjadi lowercase
    - Penghapusan angka pengalaman
    """

    if not text:
        return ""

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = text.replace("\u00a0", " ")

    lines = []
    previous_blank = False

    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()

        if not line:
            if not previous_blank and lines:
                lines.append("")

            previous_blank = True
            continue

        lines.append(line)
        previous_blank = False

    return "\n".join(lines).strip()


# ============================================================
# FILE READING
# ============================================================

def _read_uploaded_file(uploaded_file) -> bytes:
    """
    Membaca Django UploadedFile dengan aman.

    Cursor selalu dikembalikan ke posisi awal
    agar file tetap bisa disimpan oleh Django.
    """

    uploaded_file.seek(0)

    try:
        data = uploaded_file.read(MAX_FILE_BYTES + 1)
    finally:
        uploaded_file.seek(0)

    if not data:
        raise ValueError("File CV tidak boleh kosong.")

    if len(data) > MAX_FILE_BYTES:
        raise ValueError(
            "Ukuran file CV maksimal 10 MB."
        )

    return data


# ============================================================
# OCR ENGINE
# ============================================================

def _ocr_pdf_page(page, page_number: int, *, structured=False, timeout=OCR_TIMEOUT):
    """
    OCR satu halaman PDF.

    Melakukan:
    - Pembatasan jumlah piksel
    - Rendering RGB
    - OCR Indonesia + Inggris
    - Timeout per halaman
    """

    tesseract = _get_tesseract()

    if tesseract is None:
        raise ValueError(
            "Tesseract OCR tidak tersedia pada server."
        )

    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError(
            "Pillow tidak tersedia untuk OCR."
        ) from exc

    scale = OCR_DPI / 72.0

    estimated_pixels = (
        page.rect.width
        * scale
        * page.rect.height
        * scale
    )

    if estimated_pixels > MAX_OCR_PIXELS:
        raise ValueError(
            f"Halaman {page_number} terlalu besar untuk OCR."
        )

    pix = page.get_pixmap(
        dpi=OCR_DPI,
        colorspace=fitz.csRGB,
        alpha=False,
    )

    if pix.width * pix.height > MAX_OCR_PIXELS:
        raise ValueError(
            f"Resolusi halaman {page_number} melebihi batas OCR."
        )

    image = Image.frombytes(
        "RGB",
        (pix.width, pix.height),
        pix.samples,
    )

    try:
        if structured:
            return _ocr_image_result(image, tesseract, timeout)
        try:
            result = tesseract.image_to_string(
                image,
                lang="ind",
                timeout=OCR_TIMEOUT,
            )

        except Exception as exc:
            # Fallback hanya untuk masalah language data.
            # Jangan sembunyikan timeout atau error lain.
            error_message = str(exc).lower()

            language_error = any(
                marker in error_message
                for marker in (
                    "language",
                    "traineddata",
                    "failed loading",
                )
            )

            if not (
                isinstance(exc, tesseract.TesseractError)
                or language_error
            ):
                raise

            logger.warning(
                "OCR Indonesian language unavailable; "
                "retrying English."
            )

            result = tesseract.image_to_string(
                image,
                lang="eng",
                timeout=OCR_TIMEOUT,
            )

        return _normalize_text(result)

    except RuntimeError as exc:
        raise ValueError(
            f"OCR halaman {page_number} gagal "
            "atau melewati batas waktu."
        ) from exc

    except tesseract.TesseractNotFoundError as exc:
        raise ValueError(
            "Executable Tesseract tidak ditemukan."
        ) from exc

    finally:
        image.close()


def _extract_text_with_ocr(uploaded_file) -> str:
    """
    Kompatibilitas dengan fungsi OCR versi lama.

    Melakukan OCR terhadap seluruh halaman PDF,
    dengan batas MAX_OCR_PAGES.
    """

    if _get_tesseract() is None:
        raise ValueError(
            "Tesseract OCR tidak tersedia."
        )

    data = _read_uploaded_file(uploaded_file)

    if not data.startswith(b"%PDF-"):
        raise ValueError(
            "File yang diberikan bukan PDF."
        )

    try:
        doc = fitz.open(
            stream=data,
            filetype="pdf",
        )
    except Exception as exc:
        raise ValueError(
            "PDF tidak dapat dibuka untuk OCR."
        ) from exc

    try:
        if doc.needs_pass:
            raise ValueError(
                "PDF yang dilindungi password tidak didukung."
            )

        if len(doc) == 0:
            raise ValueError(
                "PDF tidak memiliki halaman."
            )

        if len(doc) > MAX_OCR_PAGES:
            raise ValueError(
                f"OCR maksimal {MAX_OCR_PAGES} halaman."
            )

        results = []

        for index, page in enumerate(doc):
            text = _ocr_pdf_page(
                page,
                index + 1,
            )

            if text:
                results.append(text)

        extracted_text = _normalize_text(
            "\n\n".join(results)
        )

        if not extracted_text:
            raise ValueError(
                "OCR tidak menemukan teks yang dapat dibaca."
            )

        return extracted_text

    finally:
        doc.close()
        uploaded_file.seek(0)


# ============================================================
# PDF EXTRACTION
# ============================================================

def _native_page_text(page):
    """Accept a simple two-column gutter only with repeated parallel blocks."""
    native = _normalize_text(page.get_text('text', sort=True))
    blocks = [b for b in page.get_text('blocks', sort=False) if b[6] == 0 and b[4].strip()]
    midpoint = (page.rect.x0 + page.rect.x1) / 2
    gutter = max(12, page.rect.width * .02)
    left = [b for b in blocks if b[2] < midpoint-gutter/2]
    right = [b for b in blocks if b[0] > midpoint+gutter/2]
    spanning = [b for b in blocks if not (b[2] < midpoint-gutter/2 or b[0] > midpoint+gutter/2)]
    if len(left) < 3 or len(right) < 3:
        warning = ['reading_order_uncertain'] if len(left) >= 2 and len(right) >= 2 else []
        return native, 'native_position_order', warning
    top = min(b[1] for b in left+right); bottom = max(b[3] for b in left+right)
    overlap = min(max(b[3] for b in left),max(b[3] for b in right))-max(min(b[1] for b in left),min(b[1] for b in right))
    height = min(max(b[3] for b in left)-min(b[1] for b in left),max(b[3] for b in right)-min(b[1] for b in right))
    date_only = all(re.fullmatch(r'[\d\s/.,–—-]*(?:(?:Jan\w*|Feb\w*|Mar\w*|Apr\w*|May|Mei|Jun\w*|Jul\w*|Aug\w*|Agu\w*|Sep\w*|Oct\w*|Okt\w*|Nov\w*|Dec\w*|Des\w*|Present|Current|Now|Sekarang)[\d\s/.,–—-]*)*', b[4].strip(), re.I) for b in right)
    label_column = sum(len(re.findall(r'\w+', b[4])) <= 3 for b in left) / len(left) >= .8
    if (date_only or label_column or max(b[2] for b in left)+gutter > min(b[0] for b in right)
        or overlap < .5*height or any(b[1] < bottom and b[3] > top for b in spanning)):
        return native, 'native_position_order', ['reading_order_uncertain']
    before = sorted([b for b in spanning if b[3] <= top],key=lambda b:(b[1],b[0]))
    after = sorted([b for b in spanning if b[1] >= bottom],key=lambda b:(b[1],b[0]))
    ordered = before+sorted(left,key=lambda b:(b[1],b[0]))+sorted(right,key=lambda b:(b[1],b[0]))+after
    return _normalize_text('\n'.join(b[4].strip() for b in ordered)), 'two_column_blocks', ['heuristic_column_order_review']


def _ocr_image_result(image, tesseract, timeout):
    """Use reported word confidence; never infer a confidence for native text."""
    language = 'ind+eng'
    deadline = time.monotonic()+timeout
    try:
        data = tesseract.image_to_data(image,lang=language,timeout=timeout,output_type=tesseract.Output.DICT)
    except Exception as exc:
        if not any(marker in str(exc).lower() for marker in ('language','traineddata','failed loading')):
            raise
        language = 'eng'
        remaining = deadline-time.monotonic()
        if remaining <= 0:raise ValueError('OCR timeout')
        data = tesseract.image_to_data(image,lang=language,timeout=remaining,output_type=tesseract.Output.DICT)
    lines = {}; confidence = []
    for i,word in enumerate(data['text']):
        if not word.strip():continue
        key = (data['block_num'][i],data['par_num'][i],data['line_num'][i])
        lines.setdefault(key,[]).append(word)
        try:value=float(data['conf'][i])
        except (ValueError,TypeError):continue
        if 0 <= value <= 100:confidence.append(value)
    text = _normalize_text('\n'.join(' '.join(words) for words in lines.values()))
    warnings = ['ocr_text_requires_review']
    if language == 'eng':warnings.append('ocr_language_fallback')
    if confidence and min(confidence) < 60:warnings.append('ocr_low_word_confidence')
    if re.search(r'\bSOL\b',text) and re.search(r'\b(?:skills?|python|django|database|postgresql|keahlian)\b',text,re.I):
        warnings.append('ambiguous_technical_token_not_corrected')
    return {'text':text,'language':language,'warnings':warnings,
            'confidence':{'source':'tesseract_word_data','scale':'0-100 engine score; not accuracy probability',
                          'mean_word_score':round(sum(confidence)/len(confidence),2),
                          'min_word_score':min(confidence),'low_word_count':sum(value<60 for value in confidence),
                          'word_count':len(confidence)} if confidence else None}


class ExtractionQualityError(ValueError):
    """Failed extraction with safe metadata, never raw exception/CV content."""
    def __init__(self, message, quality):
        super().__init__(message)
        self.quality = quality


def unknown_extraction_quality():
    return {'schema_version':'ai4a.1','status':'unknown','page_count':None,'pages':[],
            'warnings':[{'code':'legacy_extraction_quality_unavailable'}],
            'assessment_status':'limited_by_extraction',
            'interpretation':'Missing extraction metadata is not proof of complete or accurate text.'}


def _quality_result(text, format_name, pages, **extra):
    warnings = [{'page':page['page'],'code':code} for page in pages for code in page['warnings']]
    failed = [page['page'] for page in pages if page['method']=='failed']
    status = 'failed' if not text else ('partial' if failed else ('needs_review' if warnings else 'text_extracted'))
    quality = {'schema_version':'ai4a.1','format':format_name,'status':status,
               'page_count':len(pages),'pages':pages,'failed_pages':failed,
               'ocr_pages':[page['page'] for page in pages if page['ocr_attempted']],
               'ocr_failed_pages':[page['page'] for page in pages if page['ocr_status']=='failed'],
               'low_text_pages':[page['page'] for page in pages if page['native_char_count']<MIN_PAGE_TEXT_CHARS],
               'warnings':warnings,'assessment_status':'limited_by_extraction' if status!='text_extracted' else 'text_extracted',
               'interpretation':'Extraction quality is not scoring coverage or verified completeness. OCR and layout are heuristic.',**extra}
    return {'text':text,'quality':quality}


def extract_text_from_pdf(uploaded_file, *, structured=False):
    data = _read_uploaded_file(uploaded_file)
    if not data.startswith(b'%PDF-'):raise ValueError('File PDF rusak atau konten bukan PDF valid.')
    try:doc=fitz.open(stream=data,filetype='pdf')
    except Exception as exc:raise ValueError('PDF rusak atau tidak dapat dibuka.') from exc
    try:
        if doc.needs_pass:raise ValueError('PDF yang dilindungi password belum didukung.')
        if not len(doc) or len(doc)>MAX_PDF_PAGES:raise ValueError('Jumlah halaman PDF tidak didukung.')
        pages=[];texts=[];attempts=0;ocr_seconds=0
        for i,page in enumerate(doc,1):
            warnings=[]
            try:native,order,warnings=_native_page_text(page)
            except Exception:native,order,warnings='','unknown',['native_extraction_failed']
            text=native
            meta={'page':i,'method':'native_text' if native else 'failed','native_char_count':len(native),
                  'text_char_count':len(native),'reading_order':order,'warnings':warnings,
                  'ocr_attempted':False,'ocr_status':'not_needed','ocr_confidence':None}
            if len(native)<MIN_PAGE_TEXT_CHARS:
                warnings.append('low_native_text')
                if attempts>=MAX_OCR_PAGES or ocr_seconds>=MAX_OCR_TOTAL_SECONDS:
                    meta['ocr_status']='skipped_budget';warnings.append('ocr_budget_exhausted')
                elif _get_tesseract() is None:
                    meta['ocr_status']='unavailable';warnings.append('ocr_unavailable')
                else:
                    attempts+=1;meta['ocr_attempted']=True;started=time.monotonic()
                    try:
                        ocr=_ocr_pdf_page(page,i,structured=True,timeout=min(OCR_TIMEOUT,max(1,MAX_OCR_TOTAL_SECONDS-ocr_seconds)))
                        if isinstance(ocr,str):ocr={'text':ocr,'confidence':None,'warnings':['ocr_confidence_unavailable'],'language':None}
                        meta['ocr_confidence']=ocr['confidence'];meta['ocr_language']=ocr['language']
                        warnings.extend(ocr['warnings'])
                        if ocr['text'] and len(ocr['text'])>len(native):
                            text=ocr['text'];meta['method']='ocr';meta['reading_order']='ocr_engine_order';meta['ocr_status']='used'
                        else:meta['ocr_status']='native_retained';warnings.append('ocr_not_selected')
                    except Exception:
                        meta['ocr_status']='failed';warnings.append('ocr_failed_native_retained' if native else 'ocr_failed')
                    finally:ocr_seconds+=time.monotonic()-started
            if not text:meta['method']='failed';warnings.append('page_without_readable_text')
            else:texts.append(text)
            meta['text_char_count']=len(text);pages.append(meta)
        text=_normalize_text('\n\n'.join(texts))
        result=_quality_result(text,'pdf',pages)
        if not text:
            raise ExtractionQualityError('Tidak ditemukan teks yang dapat dibaca dalam PDF; OCR mungkin gagal.',result['quality'])
        return result if structured else result['text']
    finally:doc.close();uploaded_file.seek(0)


def _validate_docx_archive(data: bytes) -> None:
    """
    Validasi awal struktur DOCX.

    DOCX merupakan ZIP archive.
    Pemeriksaan ini membatasi jumlah entri dan
    ukuran deklaratif hasil dekompresi.
    """

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()

            if len(entries) > MAX_DOCX_ENTRIES:
                raise ValueError(
                    "DOCX memiliki terlalu banyak komponen."
                )

            total_uncompressed = sum(
                entry.file_size for entry in entries
            )

            if (
                total_uncompressed
                > MAX_DOCX_UNCOMPRESSED_BYTES
            ):
                raise ValueError(
                    "Ukuran konten DOCX melebihi batas."
                )

            names = set(archive.namelist())

            if "word/document.xml" not in names:
                raise ValueError(
                    "Struktur dokumen DOCX tidak valid."
                )

            if "[Content_Types].xml" not in names:
                raise ValueError(
                    "Struktur paket DOCX tidak lengkap."
                )

    except zipfile.BadZipFile as exc:
        raise ValueError(
            "File DOCX rusak atau bukan dokumen valid."
        ) from exc


def _extract_table_text(table: Table) -> list[str]:
    """
    Ambil isi tabel DOCX berdasarkan urutan baris.
    """

    results = []

    seen_cells = set()
    for row in table.rows:
        cells = []

        for cell in row.cells:
            if cell._tc in seen_cells:continue
            seen_cells.add(cell._tc)
            cell_text = _normalize_text(
                cell.text
            ).replace("\n", "; ")

            cells.append(cell_text)

        line = " | ".join(cells).strip(" |")

        if line:
            results.append(line)

    return results


def extract_text_from_docx(uploaded_file, *, structured=False):
    """
    Ekstraksi DOCX dengan menjaga urutan dokumen.

    Paragraf dan tabel diproses sesuai urutan
    kemunculannya di body dokumen.
    """

    data = _read_uploaded_file(uploaded_file)

    if data[:2] != b"PK":
        raise ValueError(
            "Konten file bukan DOCX yang valid."
        )

    _validate_docx_archive(data)

    try:
        document = Document(
            io.BytesIO(data)
        )

        text_parts = []
        paragraphs = tables = 0

        for block in document.iter_inner_content():

            if isinstance(block, Paragraph):
                paragraphs += 1
                text = _normalize_text(
                    block.text
                )

                if text:
                    text_parts.append(text)

            elif isinstance(block, Table):
                tables += 1
                table_text = _extract_table_text(
                    block
                )

                text_parts.extend(table_text)

        extracted_text = _normalize_text(
            "\n".join(text_parts)
        )

        if not extracted_text:
            raise ExtractionQualityError('DOCX tidak menghasilkan teks yang dapat dibaca.', {
                'schema_version':'ai4a.1','format':'docx','status':'failed','page_count':None,
                'pages':[], 'ocr_pages':[], 'failed_pages':[], 'ocr_failed_pages':[], 'low_text_pages':[],
                'structure':{'paragraph_count':paragraphs,'table_count':tables},
                'warnings':[{'code':'docx_no_readable_text'}],
                'assessment_status':'limited_by_extraction', 'limitations':['docx_pagination_unavailable'],
            })

        warnings = []
        if tables:warnings.append({'code':'docx_tables_linearized_row_order'})
        if len(document.inline_shapes):warnings.append({'code':'docx_images_not_extracted'})
        quality = {'schema_version':'ai4a.1','format':'docx','status':'needs_review' if warnings else 'text_extracted',
                   'page_count':None,'pages':[],'ocr_pages':[],'failed_pages':[], 'ocr_failed_pages':[], 'low_text_pages':[],
                   'structure':{'paragraph_count':paragraphs,'table_count':tables},'warnings':warnings,
                   'limitations':['docx_pagination_unavailable'],
                   'assessment_status':'limited_by_extraction' if warnings else 'text_extracted'}
        return {'text':extracted_text,'quality':quality} if structured else extracted_text

    except ValueError:
        raise

    except Exception as exc:
        logger.warning(
            "DOCX extraction failed: %s",
            type(exc).__name__,
        )

        raise ValueError(
            "DOCX tidak dapat diproses."
        ) from exc

    finally:
        uploaded_file.seek(0)


# ============================================================
# MAIN EXTRACTION ENTRY POINT
# ============================================================

def extract_document(uploaded_file):
    """Internal structured API. Metadata has no CV text, tokens or storage paths."""
    extension = Path(uploaded_file.name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:raise ValueError('Format file harus PDF atau DOCX.')
    if extension == '.pdf':return extract_text_from_pdf(uploaded_file,structured=True)
    return extract_text_from_docx(uploaded_file,structured=True)


def extract_text_from_file(uploaded_file) -> str:
    """Compatible text-only public API; structured callers use extract_document."""
    return extract_document(uploaded_file)['text']
