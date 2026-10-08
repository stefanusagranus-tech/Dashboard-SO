"""
File Reader — Universal File Parser
=====================================
Baca PDF, foto/screenshot, Excel → structured data.
"""

import io
import pandas as pd
from datetime import datetime


# =========================================================================
# DETEKSI TIPE FILE
# =========================================================================
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


# =========================================================================
# BACA PDF
# =========================================================================
def read_pdf(file_bytes):
    """Baca PDF — extract text + tabel."""
    try:
        import PyPDF2
        _pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        _text = ""
        for _page in _pdf.pages:
            _text += _page.extract_text() + "\n"

        return {
            "success": True,
            "type": "pdf",
            "text": _text.strip(),
            "error": None,
        }
    except ImportError:
        return {
            "success": False,
            "type": "pdf",
            "text": "",
            "error": "PyPDF2 gak keinstall. Tambahin `PyPDF2>=3.0.0` di requirements.txt",
        }
    except Exception as e:
        return {
            "success": False,
            "type": "pdf",
            "text": "",
            "error": f"Gagal baca PDF: {str(e)[:150]}",
        }


# =========================================================================
# BACA IMAGE (via Gemini Vision)
# =========================================================================
def read_image(file_bytes, nama_personil="", bulan=None, tahun=None):
    """
    Baca gambar — auto-detect: kalender shift atau tabel SO?
    """
    try:
        from modules.ocr_ai_handler import ocr_via_gemini, ocr_so_table, ocr_auto_detect

        # Auto-detect tipe gambar
        print(f"[FileReader] Auto-detect tipe gambar...")
        _detect = ocr_auto_detect(file_bytes)
        _detected_type = _detect.get("type", "UNKNOWN")
        print(f"[FileReader] Detected: {_detected_type}")

        # === KALAU KALENDER SHIFT ===
        if _detected_type == "SHIFT":
            if not (bulan and tahun and nama_personil):
                return {
                    "success": False,
                    "type": "image_shift",
                    "text": "",
                    "error": "Kalender shift butuh konteks: nama personil + bulan + tahun",
                }

            print(f"[FileReader] Mode SHIFT: {nama_personil} - {bulan}/{tahun}")
            _result = ocr_via_gemini(
                file_bytes,
                nama_personil=nama_personil,
                bulan=int(bulan),
                tahun=int(tahun),
            )
            if _result.get("success"):
                return {
                    "success": True,
                    "type": "image_shift",
                    "text": str(_result.get("raw_response", "")),
                    "shift_map": _result.get("shift_map", {}),
                    "error": None,
                }
            return {
                "success": False,
                "type": "image_shift",
                "text": "",
                "error": _result.get("error", "OCR shift gagal"),
            }

        # === KALAU TABEL SO atau UNKNOWN ===
        print(f"[FileReader] Mode SO_TABLE")
        _result_so = ocr_so_table(file_bytes)

        if _result_so.get("success"):
            return {
                "success": True,
                "type": "image_so_table",
                "text": _result_so.get("text", ""),
                "error": None,
                "model": _result_so.get("model", ""),
            }

        # === FALLBACK: TESSERACT ===
        print(f"[FileReader] Fallback ke Tesseract...")
        try:
            from PIL import Image
            import pytesseract
            _img = Image.open(io.BytesIO(file_bytes))
            _text = pytesseract.image_to_string(_img, lang="ind+eng")
            return {
                "success": True,
                "type": "image_ocr",
                "text": _text.strip(),
                "error": None,
                "model": "tesseract",
            }
        except Exception as _e_ocr:
            return {
                "success": False,
                "type": "image",
                "text": "",
                "error": f"OCR gagal: {_result_so.get('error', '')} | Tesseract: {str(_e_ocr)[:100]}",
            }

    except ImportError as _e:
        return {
            "success": False,
            "type": "image",
            "text": "",
            "error": f"Module gak tersedia: {str(_e)[:150]}",
        }
    except Exception as e:
        return {
            "success": False,
            "type": "image",
            "text": "",
            "error": f"Gagal baca image: {str(e)[:150]}",
        }


# =========================================================================
# BACA EXCEL / CSV
# =========================================================================
def read_excel(file_bytes, filename=""):
    """Baca Excel/CSV — return semua sheet sebagai text + dataframe."""
    try:
        _is_csv = str(filename).lower().endswith(".csv")

        if _is_csv:
            _df = pd.read_csv(io.BytesIO(file_bytes))
            _text = _df.to_string(index=False, max_rows=100)
            return {
                "success": True,
                "type": "csv",
                "text": _text,
                "sheets": {"Sheet1": _df},
                "error": None,
            }

        # Excel — baca semua sheet
        _xls = pd.ExcelFile(io.BytesIO(file_bytes))
        _all_text = []
        _sheets = {}

        for _sheet_name in _xls.sheet_names:
            _df = pd.read_excel(_xls, sheet_name=_sheet_name)
            _sheets[_sheet_name] = _df
            _all_text.append(f"=== Sheet: {_sheet_name} ===")
            _all_text.append(_df.to_string(index=False, max_rows=100))
            _all_text.append("")

        return {
            "success": True,
            "type": "excel",
            "text": "\n".join(_all_text),
            "sheets": _sheets,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "type": "excel",
            "text": "",
            "sheets": {},
            "error": f"Gagal baca Excel: {str(e)[:150]}",
        }


# =========================================================================
# UNIVERSAL READER
# =========================================================================
def read_file(file_bytes, filename, **kwargs):
    """
    Universal file reader.

    Args:
        file_bytes: bytes dari file
        filename: nama file (buat deteksi tipe)
        **kwargs: context (nama_personil, bulan, tahun)

    Returns:
        dict {
            success: bool,
            type: str,
            text: str,
            sheets: dict (kalau Excel),
            shift_map: dict (kalau image shift),
            error: str,
        }
    """
    _ftype = detect_file_type(filename)

    if _ftype == "pdf":
        return read_pdf(file_bytes)

    elif _ftype == "image":
        return read_image(
            file_bytes,
            nama_personil=kwargs.get("nama_personil", ""),
            bulan=kwargs.get("bulan"),
            tahun=kwargs.get("tahun"),
        )

    elif _ftype in ("excel", "csv"):
        return read_excel(file_bytes, filename=filename)

    else:
        return {
            "success": False,
            "type": "unknown",
            "text": "",
            "error": f"Tipe file `{_ftype}` gak didukung. Format: PDF, PNG, JPG, XLSX, CSV.",
        }