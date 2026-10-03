def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot kalender shift v2.
    
    Strategy:
    1. OCR angka tanggal (posisi baris)
    2. Deteksi warna per cell dari tengah
    3. Match tanggal + warna → kode
    """
    if not TESSERACT_AVAILABLE:
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": "Tesseract library tidak tersedia",
        }
    
    try:
        # Load image
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        
        # ============================================
        # 1. OCR TEXT — extract angka tanggal
        # ============================================
        _text = pytesseract.image_to_string(
            _img,
            config="--psm 6 -c tessedit_char_whitelist=0123456789",
        )
        
        # ✅ FIX v2: Parse angka dari text, prioritas angka 1-31
        _tanggal_detected = []
        for _line in _text.split("\n"):
            _nums = re.findall(r'\d+', _line)
            for _n in _nums:
                try:
                    _n_int = int(_n)
                    if 1 <= _n_int <= 31:
                        _tanggal_detected.append(_n_int)
                except Exception:
                    continue
        
        # Remove duplicate & sort
        _tanggal_detected = sorted(set(_tanggal_detected))
        
        # ✅ FIX: Kalau ada 1-3 tanpa 0 di depan, mungkin 01-03
        # Kalau ada 11-17 tanpa 11, coba perbaiki
        _tanggal_fixed = _fix_tanggal_sequence(_tanggal_detected)
        
        print(f"[OCR v2] Tanggal detected: {_tanggal_fixed}")
        
        # ============================================
        # 2. ANALISIS WARNA
        # ============================================
        _np_img = np.array(_img)
        
        # ✅ FIX: Grid kalender (7 kolom)
        # Layout: baris = minggu, kolom = hari (Min-Sab)
        # Kita bikin grid lebih fleksibel
        
        # Area kalender (biasanya setelah header, sebelum tombol)
        # Dari screenshot: kalender di 25%-85% tinggi
        _kalender_top = int(_h * 0.22)
        _kalender_bottom = int(_h * 0.85)
        _kalender_height = _kalender_bottom - _kalender_top
        
        # 7 kolom × 5-6 baris
        _grid_cols = 7
        _grid_rows = 5  # 5 baris biasanya cukup untuk 31 hari (31/7 ≈ 4.4)
        
        # ⚠️ KALAU ADA 6 BARIS (bulan tertentu)
        # Cek kalau ada 6 baris
        
        _cell_h = _kalender_height // _grid_rows
        _cell_w = _w // _grid_cols
        
        # ✅ FIX: Sample warna dari TENGAH cell
        _tanggal_list = []
        
        # Mapping tanggal ke posisi grid:
        # Baris 0: tanggal 1-7 (atau 01-03 dulu di kolom yang sesuai)
        # Kita perlu tau hari pertama bulan itu jatuh di hari apa
        
        # Untuk saat ini: asumsi tanggal 1 selalu di kolom ke-4 (Rabu)
        # Nanti bisa dinamis dari input user
        
        # Simplified: Ambil warna dari cell yang ada warnanya
        _cells_with_color = []
        
        for _row in range(_grid_rows):
            for _col in range(_grid_cols):
                # Posisi cell
                _y1 = _kalender_top + _row * _cell_h
                _y2 = _y1 + _cell_h
                _x1 = _col * _cell_w
                _x2 = _x1 + _cell_w
                
                # Sample TITIK TENGAH cell (bukan rata-rata)
                _center_y = (_y1 + _y2) // 2
                _center_x = (_x1 + _x2) // 2
                
                # Sample 5x5 pixel di tengah cell
                _sample_y1 = max(0, _center_y - 10)
                _sample_y2 = min(_h, _center_y + 10)
                _sample_x1 = max(0, _center_x - 10)
                _sample_x2 = min(_w, _center_x + 10)
                
                _sample = _np_img[_sample_y1:_sample_y2, _sample_x1:_sample_x2]
                
                if _sample.size == 0:
                    continue
                
                # Rata-rata warna sample
                _avg_r = int(np.median(_sample[:, :, 0]))
                _avg_g = int(np.median(_sample[:, :, 1]))
                _avg_b = int(np.median(_sample[:, :, 2]))
                
                _warna_hex = f"#{_avg_r:02X}{_avg_g:02X}{_avg_b:02X}"
                
                _cells_with_color.append({
                    "row": _row,
                    "col": _col,
                    "rgb": (_avg_r, _avg_g, _avg_b),
                    "hex": _warna_hex,
                })
        
        # ✅ Deteksi warna per cell
        for _cell in _cells_with_color:
            _r, _g, _b = _cell["rgb"]
            _kode = _rgb_to_kode_v2(_r, _g, _b)
            
            if _kode:
                _tanggal_list.append({
                    "row": _cell["row"],
                    "col": _cell["col"],
                    "kode": _kode,
                    "hex": _cell["hex"],
                    "rgb": _cell["rgb"],
                })
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "tanggal_detected": _tanggal_fixed,
            "raw_text": _text,
            "error": "",
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": str(e)[:200],
        }


def _fix_tanggal_sequence(tanggal_list):
    """
    Perbaiki sequence tanggal yang mungkin salah OCR.
    
    Contoh:
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1, 12, 13, ...] 
    → [1, 2, 3, ..., 31]
    
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, ...]
    → [1, 2, ..., 11, 12, ...]  (insert 11 yang hilang)
    """
    _fixed = sorted(set(tanggal_list))
    
    # Kalau ada 1-31 lengkap, mantap
    if len(_fixed) >= 28:
        return list(range(1, 32))
    
    # Detect "1" yang harusnya "11" (kalau ada 12-17)
    if 1 in _fixed and 12 in _fixed and 11 not in _fixed:
        _fixed.append(11)
        _fixed = sorted(set(_fixed))
    
    # Detect "2" yang harusnya "22" (kalau ada 23)
    if 2 in _fixed and 23 in _fixed and 22 not in _fixed:
        _fixed.append(22)
        _fixed = sorted(set(_fixed))
    
    return _fixed


def _rgb_to_kode_v2(r, g, b):
    """
    Deteksi kode shift dari warna RGB (v2 — lebih akurat).
    
    Warna berdasarkan screenshot:
    - Hijau tua (dark green): Pagi  → P7
    - Hijau muda (light green): Siang → S15
    - Biru/ungu: Malam → M22
    - Hitam: Off → O
    - Putih/abu: Skip (kosong)
    """
    # Filter putih/abu-abu (background kosong)
    if r > 200 and g > 200 and b > 200:
        return None
    if abs(r - g) < 15 and abs(g - b) < 15 and r > 150:
        return None
    
    # Hitam = Off
    if r < 100 and g < 100 and b < 100:
        return "O"
    
    # Biru/Ungu = Malam
    # Biru: R rendah, G rendah, B tinggi
    if b > 180 and r < 150 and g < 150:
        return "M22"
    if b > 200 and r < 120 and g < 120:
        return "M22"
    if b > 200 and r > 100 and r < 180 and g < 150:
        # Biru-ungu
        return "M22"
    
    # Hijau = Pagi atau Siang
    # Hijau punya G > R dan G > B
    if g > r and g > b:
        # Hijau muda (terang) = Siang
        if g > 180 and r > 80:
            return "S15"
        # Hijau tua = Pagi
        if g > 100 and g < 180:
            return "P7"
        # Fallback hijau
        return "S15"
    
    # Coklat/tan (kuning muda)
    if r > 180 and g > 150 and b < 150:
        return "O"  # atau maybe P7
    
    # Default: skip
    return None