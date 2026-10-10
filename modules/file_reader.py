"""
File Reader — Universal File Parser v3
========================================
Layer fallback:
1. Excel/CSV → pandas (prioritas 1)
2. PDF → pdfplumber (prioritas 2)
3. PDF text → fallback (prioritas 3)
4. Screenshot → Gemini OCR (prioritas 4)
5. Unknown → error
"""

import io
import re
import pandas as pd
from datetime import datetime


# =========================================================
# LOG BUFFER
# =========================================================
_LOG_BUFFER = []


def set_log_buffer(buffer):
    global _LOG_BUFFER
    _LOG_BUFFER = buffer


def _log(msg):
    print(msg)
    try:
        _LOG_BUFFER.append(str(msg))
    except Exception:
        pass


# =========================================================
# DETEKSI TIPE FILE
# =========================================================
def detect_file_type(filename):
    """Deteksi tipe file dari extension."""
    _name = str(filename).lower()
    if _name.endswith(".pdf"):
        return "pdf"
    elif _name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    elif _name.endswith((".xlsx", ".xls")):
        return "excel"
    elif _name.endswith(".csv"):
        return "csv"
    return "unknown"


# =========================================================
# 📊 LAYER 1: EXCEL/CSV → pandas
# =========================================================
def read_excel(file_bytes, filename=""):
    """Baca Excel/CSV."""
    try:
        _is_csv = str(filename).lower().endswith(".csv")

        if _is_csv:
            _df = pd.read_csv(io.BytesIO(file_bytes))
            _text = _df.to_string(index=False, max_rows=100)
            _log(f"[Excel] CSV loaded: {_df.shape}")
            return {
                "success": True,
                "type": "csv",
                "text": _text,
                "primary_df": _df,
                "error": None,
            }

        _xls = pd.ExcelFile(io.BytesIO(file_bytes))
        _all_text = []
        _sheets = {}
        _primary_df = None

        for _sheet_name in _xls.sheet_names:
            _df = pd.read_excel(_xls, sheet_name=_sheet_name)
            _sheets[_sheet_name] = _df

            if _primary_df is None and len(_df) > 0:
                _primary_df = _df

            _all_text.append(f"=== Sheet: {_sheet_name} ===")
            _all_text.append(_df.to_string(index=False, max_rows=100))
            _all_text.append("")

        _log(f"[Excel] Loaded {len(_xls.sheet_names)} sheets")

        return {
            "success": True,
            "type": "excel",
            "text": "\n".join(_all_text),
            "primary_df": _primary_df,
            "error": None,
        }
    except Exception as e:
        _log(f"[Excel] Error: {e}")
        return {
            "success": False,
            "type": "excel",
            "text": "",
            "primary_df": None,
            "error": f"Gagal baca Excel: {str(e)[:150]}",
        }


# =========================================================
# 📄 LAYER 2: PDF → pdfplumber
# =========================================================
def read_pdf_plumber(file_bytes):
    """Baca PDF pake pdfplumber — extract tabel otomatis."""
    try:
        import pdfplumber

        _all_text = []
        _all_tables = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as _pdf:
            _total_pages = len(_pdf.pages)
            _log(f"[PDF] pdfplumber: {_total_pages} pages")

            for _i, _page in enumerate(_pdf.pages):
                # Extract text
                _page_text = _page.extract_text() or ""
                _all_text.append(_page_text)

                # Extract tables
                _tables = _page.extract_tables()
                if _tables:
                    _log(f"[PDF] Page {_i+1}: {len(_tables)} table(s) found")
                    for _table in _tables:
                        if _table and len(_table) > 1:
                            _all_tables.append(_table)

        _full_text = "\n".join(_all_text)
        _log(f"[PDF] pdfplumber extracted: {len(_full_text)} chars, {len(_all_tables)} tables")

        # Convert first table ke DataFrame
        _primary_df = None
        if _all_tables:
            _table = _all_tables[0]
            try:
                _headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(_table[0])]
                _rows = _table[1:]
                _primary_df = pd.DataFrame(_rows, columns=_headers)
                _log(f"[PDF] Primary DataFrame: {_primary_df.shape}")
            except Exception as _e:
                _log(f"[PDF] Table to DataFrame error: {_e}")

        if not _full_text and _primary_df is None:
            _log(f"[PDF] pdfplumber got empty result")
            return {"success": False, "error": "PDF kosong / gak ada text"}

        return {
            "success": True,
            "type": "pdf",
            "text": _full_text,
            "primary_df": _primary_df,
            "error": None,
        }

    except ImportError:
        _log("[PDF] pdfplumber gak keinstall")
        return {"success": False, "error": "pdfplumber gak keinstall. Tambahin di requirements.txt"}
    except Exception as e:
        _log(f"[PDF] pdfplumber error: {e}")
        return {"success": False, "error": f"pdfplumber error: {str(e)[:150]}"}


# =========================================================
# 📄 LAYER 3: PDF → PyPDF2 (fallback text)
# =========================================================
def read_pdf_pypdf2(file_bytes):
    """Baca PDF pake PyPDF2 — fallback kalau pdfplumber gagal."""
    try:
        import PyPDF2
        _pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        _text = ""
        for _page in _pdf.pages:
            _text += _page.extract_text() + "\n"

        _log(f"[PDF] PyPDF2 fallback: {len(_text)} chars from {len(_pdf.pages)} pages")

        return {
            "success": True,
            "text": _text.strip(),
            "primary_df": None,
            "error": None,
        }
    except Exception as e:
        _log(f"[PDF] PyPDF2 error: {e}")
        return {"success": False, "text": "", "primary_df": None, "error": str(e)[:150]}


# =========================================================
# 📄 READ PDF — multi-layer
# =========================================================
def read_pdf(file_bytes):
    """Baca PDF — extract text aja, jangan jadi DataFrame."""
    # Layer 1: pdfplumber text only
    try:
        import pdfplumber
        _all_text = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as _pdf:
            for _page in _pdf.pages:
                _page_text = _page.extract_text() or ""
                _all_text.append(_page_text)

        _full_text = "\n".join(_all_text)
        _log(f"[PDF] pdfplumber text: {len(_full_text)} chars")

        if _full_text.strip():
            return {
                "success": True,
                "type": "pdf",
                "text": _full_text,
                "primary_df": None,
                "error": None,
            }
    except Exception as _e:
        _log(f"[PDF] pdfplumber error: {_e}")

    # Layer 2: PyPDF2 fallback
    try:
        import PyPDF2
        _pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        _text = ""
        for _page in _pdf.pages:
            _text += _page.extract_text() + "\n"

        _log(f"[PDF] PyPDF2: {len(_text)} chars")
        return {
            "success": True,
            "type": "pdf",
            "text": _text.strip(),
            "primary_df": None,
            "error": None,
        }
    except Exception as _e:
        return {
            "success": False, "type": "pdf", "text": "",
            "primary_df": None, "error": str(_e)[:150],
        }


# =========================================================
# 📸 LAYER 4: IMAGE → Gemini OCR
# =========================================================
def read_image(file_bytes, nama_personil="", bulan=None, tahun=None):
    """Baca gambar — Gemini OCR."""
    try:
        from modules.ocr_ai_handler import ocr_via_gemini, ocr_so_table, ocr_auto_detect

        _log("[FileReader] Auto-detect tipe gambar...")
        _detect = ocr_auto_detect(file_bytes)
        _detected_type = _detect.get("type", "UNKNOWN")
        _log(f"[FileReader] Detected: {_detected_type}")

        # Kalender shift
        if _detected_type == "SHIFT":
            if not (bulan and tahun and nama_personil):
                return {
                    "success": False,
                    "type": "image_shift",
                    "text": "",
                    "primary_df": None,
                    "error": "Kalender shift butuh konteks",
                }

            _result = ocr_via_gemini(file_bytes, nama_personil=nama_personil,
                                     bulan=int(bulan), tahun=int(tahun))
            if _result.get("success"):
                return {
                    "success": True,
                    "type": "image_shift",
                    "text": str(_result.get("raw_response", "")),
                    "shift_map": _result.get("shift_map", {}),
                    "primary_df": None,
                    "error": None,
                }
            return {
                "success": False,
                "type": "image_shift",
                "text": "",
                "primary_df": None,
                "error": _result.get("error", "OCR shift gagal"),
            }

        # Tabel SO
        _log("[FileReader] Mode SO_TABLE")
        _result_so = ocr_so_table(file_bytes)

        if _result_so.get("success"):
            _text = _result_so.get("text", "")
            _log(f"[FileReader] SO OCR success: {len(_text)} chars")
            return {
                "success": True,
                "type": "image_so_table",
                "text": _text,
                "primary_df": None,
                "error": None,
                "model": _result_so.get("model", ""),
            }

        return {
            "success": False,
            "type": "image",
            "text": "",
            "primary_df": None,
            "error": _result_so.get("error", "OCR gagal"),
        }

    except ImportError as _e:
        return {
            "success": False, "type": "image", "text": "",
            "primary_df": None, "error": f"Module gak tersedia: {str(_e)[:150]}",
        }
    except Exception as e:
        return {
            "success": False, "type": "image", "text": "",
            "primary_df": None, "error": f"Gagal baca image: {str(e)[:150]}",
        }


# =========================================================
# UNIVERSAL READER
# =========================================================
def read_file(file_bytes, filename, **kwargs):
    """Universal file reader — multi-layer."""
    _ftype = detect_file_type(filename)
    _log(f"[FileReader] Type: {_ftype} | File: {filename}")

    if _ftype in ("excel", "csv"):
        return read_excel(file_bytes, filename=filename)

    if _ftype == "pdf":
        return read_pdf(file_bytes)

    if _ftype == "image":
        return read_image(
            file_bytes,
            nama_personil=kwargs.get("nama_personil", ""),
            bulan=kwargs.get("bulan"),
            tahun=kwargs.get("tahun"),
        )

    return {
        "success": False,
        "type": "unknown",
        "text": "",
        "primary_df": None,
        "error": f"Tipe file `{_ftype}` gak didukung.",
    }