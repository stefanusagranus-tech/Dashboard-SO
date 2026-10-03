def ocr_kalender_screenshot(image_bytes):
    """
    OCR screenshot v7 — Auto-detect grid dari screenshot.
    """
    if not TESSERACT_AVAILABLE:
        return {
            "success": False,
            "tanggal_list": [],
            "raw_text": "",
            "error": "Tesseract tidak tersedia",
        }
    
    try:
        _img = Image.open(io.BytesIO(image_bytes))
        if _img.mode != "RGB":
            _img = _img.convert("RGB")
        
        _w, _h = _img.size
        print(f"[OCR v7] Image: {_w}x{_h}")
        
        # ============================================
        # OCR TEXT FULL (untuk debug)
        # ============================================
        _text_full = pytesseract.image_to_string(_img, config="--psm 6")
        
        _np_img = np.array(_img)
        
        # ============================================
        # 1. AUTO-DETECT AREA KALENDER
        # ============================================
        # Cari baris yang BUKAN putih/abu terang (ada warna)
        _grayscale = np.mean(_np_img, axis=2)
        _is_white = _grayscale > 230
        
        # Hitung berapa pixel warna di tiap baris
        _row_color_density = 1 - np.mean(_is_white, axis=1)
        
        # Cari baris pertama yang mulai ada warna
        _kalender_start = None
        _kalender_end = None
        
        # Scan dari atas, cari density > 0.1 (artinya ada warna)
        for _i in range(int(_h * 0.3), _h - 10):
            if _row_color_density[_i] > 0.10:
                if _kalender_start is None:
                    _kalender_start = _i
                _kalender_end = _i
        
        # Fallback
        if _kalender_start is None:
            _kalender_start = int(_h * 0.55)
            _kalender_end = int(_h * 0.95)
        
        _kalender_height = _kalender_end - _kalender_start
        print(f"[OCR v7] Kalender area: y={_kalender_start}-{_kalender_end}, h={_kalender_height}")
        
        # ============================================
        # 2. AUTO-DETECT KOLOM
        # ============================================
        # Cari kolom yang ada warna di area kalender
        _kalender_region = _np_img[_kalender_start:_kalender_end, :]
        _region_gray = np.mean(_kalender_region, axis=2)
        _region_white = _region_gray > 230
        
        _col_color_density = 1 - np.mean(_region_white, axis=0)
        
        # Deteksi start/end tiap kolom
        _col_starts = []
        _col_ends = []
        _in_col = False
        
        for _i in range(_w):
            if _col_color_density[_i] > 0.10:
                if not _in_col:
                    _col_starts.append(_i)
                    _in_col = True
            else:
                if _in_col:
                    _col_ends.append(_i)
                    _in_col = False
        
        if _in_col:
            _col_ends.append(_w)
        
        print(f"[OCR v7] Kolom detected: {len(_col_starts)}")
        
        # ============================================
        # 3. AUTO-DETECT ROW (per minggu)
        # ============================================
        _row_color_density_kal = _row_color_density[_kalender_start:_kalender_end]
        
        _row_starts = []
        _row_ends = []
        _in_row = False
        
        for _i in range(len(_row_color_density_kal)):
            if _row_color_density_kal[_i] > 0.05:
                if not _in_row:
                    _row_starts.append(_i)
                    _in_row = True
            else:
                if _in_row:
                    _row_ends.append(_i)
                    _in_row = False
        
        if _in_row:
            _row_ends.append(len(_row_color_density_kal))
        
        print(f"[OCR v7] Baris detected: {len(_row_starts)}")
        
        # ============================================
        # 4. FALLBACK KALAU AUTO-DETECT GAGAL
        # ============================================
        if len(_col_starts) < 5 or len(_row_starts) < 4:
            # Pakai grid fixed
            print(f"[OCR v7] Fallback: pakai grid fixed 7×5")
            _grid_cols = 7
            _grid_rows = 5
            _cell_h = _kalender_height // _grid_rows
            _cell_w = _w // _grid_cols
            
            _col_starts = [_c * _cell_w for _c in range(_grid_cols)]
            _col_ends = [(_c + 1) * _cell_w for _c in range(_grid_cols)]
            _row_starts = [_r * _cell_h for _r in range(_grid_rows)]
            _row_ends = [(_r + 1) * _cell_h for _r in range(_grid_rows)]
        
        # ============================================
        # 5. ANALISIS PER CELL
        # ============================================
        _tanggal_list = []
        _debug_info = []
        
        # Iterasi kombinasi row × col
        for _r_idx, (_y_start, _y_end) in enumerate(zip(_row_starts, _row_ends)):
            for _c_idx, (_x_start, _x_end) in enumerate(zip(_col_starts, _col_ends)):
                # Skip cell yang terlalu kecil
                if (_x_end - _x_start) < 20 or (_y_end - _y_start) < 15:
                    continue
                
                # Absolute position
                _y1 = _kalender_start + _y_start
                _y2 = _kalender_start + _y_end
                _x1 = _x_start
                _x2 = _x_end
                
                # Crop cell
                _cell_img = _img.crop((_x1, _y1, _x2, _y2))
                _cell_np = np.array(_cell_img)
                
                if _cell_np.size == 0:
                    continue
                
                # Skip cell yang putih (kosong)
                _cell_gray = np.mean(_cell_np, axis=2)
                _cell_white_pct = np.mean(_cell_gray > 230)
                
                if _cell_white_pct > 0.85:
                    continue
                
                # ============================================
                # DETEKSI WARNA
                # ============================================
                _h_cell, _w_cell = _cell_np.shape[:2]
                _points = [
                    _cell_np[_h_cell // 2, _w_cell // 2],
                    _cell_np[_h_cell // 3, _w_cell // 3],
                    _cell_np[_h_cell // 3, 2 * _w_cell // 3],
                ]
                
                _r_val = int(np.median([p[0] for p in _points]))
                _g_val = int(np.median([p[1] for p in _points]))
                _b_val = int(np.median([p[2] for p in _points]))
                
                _kode_warna, _conf_warna, _dist = _rgb_to_kode_v2(_r_val, _g_val, _b_val)
                
                # ============================================
                # DETEKSI TEXT CELL
                # ============================================
                _kode_huruf = None
                _text_cell = ""
                
                try:
                    _text_cell = pytesseract.image_to_string(
                        _cell_img,
                        config="--psm 7",
                    ).strip()
                    
                    if _text_cell:
                        _kode_huruf, _conf_huruf = _huruf_to_kode(_text_cell)
                except Exception:
                    pass
                
                # ============================================
                # VOTING
                # ============================================
                _kode_final = None
                _confidence = "LOW"
                _sumber = ""
                
                if _kode_huruf and _kode_warna:
                    if _kode_huruf == _kode_warna:
                        _kode_final = _kode_huruf
                        _confidence = "HIGH"
                        _sumber = "huruf+warna"
                    else:
                        _kode_final = _kode_huruf
                        _confidence = "MEDIUM"
                        _sumber = f"huruf({_kode_huruf}) vs warna({_kode_warna})"
                elif _kode_huruf:
                    _kode_final = _kode_huruf
                    _confidence = "MEDIUM"
                    _sumber = "huruf"
                elif _kode_warna:
                    _kode_final = _kode_warna
                    _confidence = "MEDIUM"
                    _sumber = "warna"
                
                _debug_info.append({
                    "row": _r_idx,
                    "col": _c_idx,
                    "x": (_x1, _x2),
                    "y": (_y1, _y2),
                    "text_cell": _text_cell,
                    "kode_huruf": _kode_huruf,
                    "kode_warna": _kode_warna,
                    "rgb": (_r_val, _g_val, _b_val),
                    "final": _kode_final,
                })
                
                if _kode_final:
                    _tanggal_list.append({
                        "row": _r_idx,
                        "col": _c_idx,
                        "kode": _kode_final,
                        "confidence": _confidence,
                        "sumber": _sumber,
                        "rgb": (_r_val, _g_val, _b_val),
                    })
        
        print(f"[OCR v7] Detected: {len(_tanggal_list)} cells")
        
        return {
            "success": True,
            "tanggal_list": _tanggal_list,
            "debug_cells": _debug_info,
            "kolom_detected": len(_col_starts),
            "baris_detected": len(_row_starts),
            "raw_text": _text_full,
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