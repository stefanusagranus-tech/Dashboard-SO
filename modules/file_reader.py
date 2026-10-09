"""
File Reader — Universal File Parser v2
========================================
Baca PDF, foto/screenshot, Excel → structured data.
Plus logger buffer buat debug UI.
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
    """Set external log buffer dari halaman Yui."""
    global _LOG_BUFFER
    _LOG_BUFFER = buffer


def _log(msg):
    """Internal logger — print + kirim ke buffer."""
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
# BACA PDF
# =========================================================
def read_pdf(file_bytes):
    """Baca PDF — extract text."""
    try:
        import PyPDF2
        _pdf = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        _text = ""
        for _page in _pdf.pages:
            _text += _page.extract_text() + "\n"

        _log(f"[PDF] Extracted {len(_text)} chars from {len(_pdf.pages)} pages")

        return {
            "success": True,
            "type": "pdf",
            "text": _text.strip(),
            "error": None,
        }
    except ImportError:
        _log("[PDF] PyPDF2 not installed")
        return {
            "success": False,
            "type": "pdf",
            "text": "",
            "error": "PyPDF2 gak keinstall. Tambahin `PyPDF2>=3.0.0` di requirements.txt",
        }
    except Exception as e:
        _log(f"[PDF] Error: {e}")
        return {
            "success": False,
            "type": "pdf",
            "text": "",
            "error": f"Gagal baca PDF: {str(e)[:150]}",
        }


# =========================================================
# BACA IMAGE
# =========================================================
def read_image(file_bytes, nama_personil="", bulan=None, tahun=None):
    """Baca gambar — auto-detect tipe (kalender shift / tabel SO)."""
    try:
        from modules.ocr_ai_handler import ocr_via_gemini, ocr_so_table, ocr_auto_detect

        _log("[FileReader] Auto-detect tipe gambar...")
        _detect = ocr_auto_detect(file_bytes)
        _detected_type = _detect.get("type", "UNKNOWN")
        _log(f"[FileReader] Detected: {_detected_type}")

        # === KALENDER SHIFT ===
        if _detected_type == "SHIFT":
            if not (bulan and tahun and nama_personil):
                _log("[FileReader] Shift mode butuh konteks (bulan/tahun/nama)")
                return {
                    "success": False,
                    "type": "image_shift",
                    "text": "",
                    "error": "Kalender shift butuh konteks: nama personil + bulan + tahun",
                }

            _log(f"[FileReader] Mode SHIFT: {nama_personil} - {bulan}/{tahun}")
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
            _log(f"[FileReader] Shift OCR error: {_result.get('error', '')}")
            return {
                "success": False,
                "type": "image_shift",
                "text": "",
                "error": _result.get("error", "OCR shift gagal"),
            }

        # === TABEL SO ===
        _log("[FileReader] Mode SO_TABLE")
        _result_so = ocr_so_table(file_bytes)

        if _result_so.get("success"):
            _text = _result_so.get("text", "")
            _log(f"[FileReader] SO table OCR success: {len(_text)} chars, model={_result_so.get('model', '')}")
            return {
                "success": True,
                "type": "image_so_table",
                "text": _text,
                "error": None,
                "model": _result_so.get("model", ""),
            }

        _log(f"[FileReader] SO table OCR failed: {_result_so.get('error', '')}")

        # === FALLBACK TESSERACT ===
        _log("[FileReader] Fallback ke Tesseract...")
        try:
            from PIL import Image
            import pytesseract
            _img = Image.open(io.BytesIO(file_bytes))
            _text = pytesseract.image_to_string(_img, lang="ind+eng")
            _log(f"[FileReader] Tesseract extracted: {len(_text)} chars")
            return {
                "success": True,
                "type": "image_ocr",
                "text": _text.strip(),
                "error": None,
                "model": "tesseract",
            }
        except Exception as _e_ocr:
            _log(f"[FileReader] Tesseract failed: {_e_ocr}")
            return {
                "success": False,
                "type": "image",
                "text": "",
                "error": f"OCR gagal: {_result_so.get('error', '')} | Tesseract: {str(_e_ocr)[:100]}",
            }

    except ImportError as _e:
        _log(f"[FileReader] Import error: {_e}")
        return {
            "success": False,
            "type": "image",
            "text": "",
            "error": f"Module gak tersedia: {str(_e)[:150]}",
        }
    except Exception as e:
        _log(f"[FileReader] Error: {e}")
        return {
            "success": False,
            "type": "image",
            "text": "",
            "error": f"Gagal baca image: {str(e)[:150]}",
        }


# =========================================================
# BACA EXCEL / CSV
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
                "sheets": {"Sheet1": _df},
                "error": None,
            }

        _xls = pd.ExcelFile(io.BytesIO(file_bytes))
        _all_text = []
        _sheets = {}

        for _sheet_name in _xls.sheet_names:
            _df = pd.read_excel(_xls, sheet_name=_sheet_name)
            _sheets[_sheet_name] = _df
            _all_text.append(f"=== Sheet: {_sheet_name} ===")
            _all_text.append(_df.to_string(index=False, max_rows=100))
            _all_text.append("")

        _log(f"[Excel] Loaded {len(_xls.sheet_names)} sheets")

        return {
            "success": True,
            "type": "excel",
            "text": "\n".join(_all_text),
            "sheets": _sheets,
            "error": None,
        }
    except Exception as e:
        _log(f"[Excel] Error: {e}")
        return {
            "success": False,
            "type": "excel",
            "text": "",
            "sheets": {},
            "error": f"Gagal baca Excel: {str(e)[:150]}",
        }

# =========================================================
# 🔄 CONVERT OCR TEXT → DataFrame (buat PDF/Screenshot)
# =========================================================
def convert_ocr_to_dataframe(ocr_text, file_type="pdf"):
    """
    Convert OCR text (dari PDF/Screenshot) → DataFrame.
    FIX v2 — handle:
    - Kolom Fisik = "-" (kosong)
    - Qty var = "+27" / "-1" 
    - Nama nempel angka (SPICYKOREAN60G)
    """
    import re
    import pandas as pd

    if not ocr_text or not str(ocr_text).strip():
        _log("[Convert] OCR text kosong")
        return None

    _text = str(ocr_text)
    _rows = []

    _log(f"[Convert] Converting OCR text ({len(_text)} chars) → DataFrame")

    # ✅ PATTERN BARU — lebih fleksibel
    # Format: No PLU Nama... Rak Stock Fisik(+) QtyVar(+/-) Nominal(+/-)
    # Handle: Fisik bisa "-", QtyVar bisa "+27", Nama bisa nempel angka
    _pattern = re.compile(
        r'^\s*(\d{1,3})\s+'                              # No
        r'(\d{5,})\s+'                                   # PLU
        r'(.+?)\s+'                                      # Nama (non-greedy, ambil apapun)
        r'(Q\d{1,3}|QA\d{1,3}|O[A-Z]\d{1,2}|\d{2,4})\s+' # Rak
        r'(-?\d+)\s+'                                    # Stock
        r'(-|\d+)\s+'                                    # Fisik ("-" atau angka)
        r'([-+]?\d+)\s+'                                 # Qty Var (+ atau -)
        r'([-+]?[\d,]+\.?\d*)\s*$',                      # Nominal
        re.MULTILINE
    )

    for _match in _pattern.finditer(_text):
        try:
            _no = int(_match.group(1))
            _plu = _match.group(2).strip()
            _nama = _match.group(3).strip()[:120]
            _rak = _match.group(4).strip().upper()
            _qty_stock = int(_match.group(5))
            
            _fisik_str = _match.group(6).strip()
            _qty_fisik = int(_fisik_str) if _fisik_str != "-" else 0
            
            _qty_var = int(_match.group(7))
            
            _nominal_str = _match.group(8).replace(",", "")
            _nominal = float(_nominal_str)

            _rows.append({
                "No": _no,
                "PLU": _plu,
                "Nama Barang": _nama,
                "Rack": _rak,
                "Stock Fisik": _qty_fisik,
                "Stock Onhand": _qty_stock,
                "Plus/Minus": _qty_var,
                "Selisih Rupiah": _nominal,
            })
        except Exception as _e:
            _log(f"[Convert] Row error: {_e} | line: {_match.group(0)[:80]}")
            continue

    if not _rows:
        _log(f"[Convert] Pattern gagal. 0 rows")
        return None

    _df = pd.DataFrame(_rows)
    _log(f"[Convert] SUCCESS: {len(_df)} rows → DataFrame")

    return _df


# =========================================================
# 🔄 PARSE GEMINI MARKDOWN TABLE
# =========================================================
def parse_gemini_markdown_table(markdown_text):
    """Parse Gemini markdown table output → DataFrame."""
    import re
    import pandas as pd

    if not markdown_text:
        return None

    _text = str(markdown_text)
    _lines = _text.splitlines()

    _rows = []
    _in_table = False
    _header_found = False

    for _line in _lines:
        _line = _line.strip()

        if _line.startswith("|") and _line.endswith("|"):
            if re.match(r'^[\|\s\-:]+$', _line):
                continue

            _cells = [c.strip() for c in _line.split("|")[1:-1]]
            if not _cells:
                continue

            if not _header_found:
                _header_found = True
                _in_table = True
                continue

            if _in_table:
                _rows.append(_cells)
        else:
            if _in_table and _rows:
                break

    if not _rows:
        return None

    _max_cols = max(len(r) for r in _rows)
    _normalized = []
    for _r in _rows:
        while len(_r) < _max_cols:
            _r.append("")
        _normalized.append(_r)

    _col_names = [f"col_{i}" for i in range(_max_cols)]

    _df = pd.DataFrame(_normalized, columns=_col_names)

    _log(f"[Convert] Markdown table parsed: {len(_df)} rows × {_max_cols} cols")

    return _df

# =========================================================
# UNIVERSAL READER
# =========================================================
def read_file(file_bytes, filename, **kwargs):
    """Universal file reader — auto-convert PDF/Screenshot ke DataFrame."""
    _ftype = detect_file_type(filename)
    _log(f"[FileReader] Type: {_ftype} | File: {filename}")

    # === EXCEL/CSV ===
    if _ftype in ("excel", "csv"):
        return read_excel(file_bytes, filename=filename)

    # === PDF ===
    if _ftype == "pdf":
        _pdf_result = read_pdf(file_bytes)

        if _pdf_result.get("success") and _pdf_result.get("text"):
            _df = convert_ocr_to_dataframe(_pdf_result["text"], file_type="pdf")
            _pdf_result["primary_df"] = _df
            _pdf_result["converted_df"] = _df is not None
            _log(f"[FileReader] PDF → DataFrame: {'OK' if _df is not None else 'FAILED'}")

        return _pdf_result

    # === IMAGE ===
    if _ftype == "image":
        _img_result = read_image(
            file_bytes,
            nama_personil=kwargs.get("nama_personil", ""),
            bulan=kwargs.get("bulan"),
            tahun=kwargs.get("tahun"),
        )

        if _img_result.get("success") and _img_result.get("text"):
            _df = convert_ocr_to_dataframe(
                _img_result["text"],
                file_type=_img_result.get("type", "image_ocr"),
            )
            _img_result["primary_df"] = _df
            _img_result["converted_df"] = _df is not None
            _log(f"[FileReader] Image → DataFrame: {'OK' if _df is not None else 'FAILED'}")

        return _img_result

    # === UNKNOWN ===
    _log(f"[FileReader] Unknown type: {_ftype}")
    return {
        "success": False,
        "type": "unknown",
        "text": "",
        "primary_df": None,
        "error": f"Tipe file `{_ftype}` gak didukung.",
    }