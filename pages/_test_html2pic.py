"""
Test html2pic — Cek apakah html2pic works di Streamlit Cloud.
"""
import streamlit as st
import io
import os
import tempfile


st.set_page_config(page_title="Test html2pic", page_icon="🧪")
st.title("Test html2pic")


_html = """
<html>
<body style="font-family: Arial; padding: 20px; background: #F0EEEA; margin: 0;">
    <div style="background: #97B3AE; color: white; padding: 20px; border-radius: 12px;">
        <h1 style="margin: 0; font-size: 24px;">TEST HEADER</h1>
        <p style="margin: 5px 0 0; font-size: 14px;">Toko C383 - 10/10/2026</p>
    </div>
    <div style="display: flex; gap: 12px; margin-top: 20px;">
        <div style="flex: 1; background: #D2E0D3; padding: 15px; border-radius: 10px;">
            <small style="color: #3C3C3C;">TOTAL RAK</small>
            <h2 style="margin: 5px 0; color: #3C3C3C; font-size: 20px;">3 rak</h2>
        </div>
        <div style="flex: 1; background: #F0DDD6; padding: 15px; border-radius: 10px;">
            <small style="color: #3C3C3C;">TOTAL ITEM</small>
            <h2 style="margin: 5px 0; color: #3C3C3C; font-size: 20px;">21 item</h2>
        </div>
        <div style="flex: 1; background: #F2C3B9; padding: 15px; border-radius: 10px;">
            <small style="color: #3C3C3C;">TOTAL NOMINAL</small>
            <h2 style="margin: 5px 0; color: #3C3C3C; font-size: 20px;">-Rp 34.556</h2>
        </div>
    </div>
</body>
</html>
"""


if st.button("Test Render", type="primary"):
    try:
        from html2pic import Html2Pic
        
        _render = Html2Pic(_html)
        _image = _render.render()
        
        st.info(f"✅ Render berhasil! Tipe objek: `{type(_image)}`")
        
        # === COBA SAVE DENGAN BERBAGAI CARA ===
        _saved = False
        _img_bytes = None
        _last_err = None
        
        # Cara 1: save ke temp file (paling umum)
        try:
            _tmp_path = os.path.join(tempfile.gettempdir(), "test_html2pic.png")
            _image.save(_tmp_path)
            with open(_tmp_path, "rb") as _f:
                _img_bytes = _f.read()
            if _img_bytes and len(_img_bytes) > 100:
                _saved = True
                st.success("✅ Save berhasil (Cara 1: `_image.save(path)`)")
        except Exception as _e1:
            _last_err = f"Cara 1 gagal: {_e1}"
            st.warning(_last_err)
        
        # Cara 2: save dengan format arg
        if not _saved:
            try:
                _tmp_path2 = os.path.join(tempfile.gettempdir(), "test_html2pic_2.png")
                _image.save(_tmp_path2, "PNG")
                with open(_tmp_path2, "rb") as _f:
                    _img_bytes = _f.read()
                if _img_bytes and len(_img_bytes) > 100:
                    _saved = True
                    st.success("✅ Save berhasil (Cara 2: `_image.save(path, 'PNG')`)")
            except Exception as _e2:
                _last_err = f"Cara 2 gagal: {_e2}"
                st.warning(_last_err)
        
        # Cara 3: encodeToData + PIL
        if not _saved:
            try:
                from PIL import Image as PILImage
                _data = _image.encodeToData()
                _bytes = _data.bytes() if hasattr(_data, "bytes") else bytes(_data)
                _pil = PILImage.open(io.BytesIO(_bytes))
                _buf = io.BytesIO()
                _pil.save(_buf, format="PNG")
                _img_bytes = _buf.getvalue()
                if _img_bytes and len(_img_bytes) > 100:
                    _saved = True
                    st.success("✅ Save berhasil (Cara 3: `encodeToData` + PIL)")
            except Exception as _e3:
                _last_err = f"Cara 3 gagal: {_e3}"
                st.warning(_last_err)
        
        # Cara 4: toarray + PIL
        if not _saved:
            try:
                from PIL import Image as PILImage
                import numpy as np
                _arr = _image.toarray()
                _pil = PILImage.fromarray(np.array(_arr))
                _buf = io.BytesIO()
                _pil.save(_buf, format="PNG")
                _img_bytes = _buf.getvalue()
                if _img_bytes and len(_img_bytes) > 100:
                    _saved = True
                    st.success("✅ Save berhasil (Cara 4: `toarray` + PIL)")
            except Exception as _e4:
                _last_err = f"Cara 4 gagal: {_e4}"
                st.warning(_last_err)
        
        # === HASIL ===
        if _saved and _img_bytes:
            st.markdown("---")
            st.markdown("### 📸 Hasil")
            st.image(_img_bytes, caption="Hasil html2pic")
            st.success("🎉 **html2pic WORKS!** Siap dipakai buat infografis.")
        else:
            st.error(f"❌ Semua cara save gagal. Error terakhir: {_last_err}")
            st.markdown("**Detail objek `_image`:**")
            st.code(f"Tipe: {type(_image)}\nDir: {[m for m in dir(_image) if not m.startswith('_')]}")
    
    except Exception as e:
        import traceback
        st.error(f"❌ html2pic GAGAL:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")
