"""
Test html2pic — Eksperimen 2: Inline CSS only.
"""
import streamlit as st
import os
import tempfile


st.set_page_config(page_title="Test html2pic", page_icon="🧪")
st.title("Test html2pic - Eksperimen 2")


_html = """
<html>
<body style="background-color: #F0EEEA; margin: 0; padding: 40px; width: 1080px;">

    <div style="background-color: #97B3AE; padding: 30px; margin-bottom: 30px;">
        <div style="font-size: 36px; color: #FFFFFF; font-weight: bold; margin-bottom: 10px;">
            ANALISIS GAMBARAN SO
        </div>
        <div style="font-size: 18px; color: #F0EEEA;">
            Toko C383 - Karang Satria - 10/10/2026
        </div>
    </div>

    <div style="display: flex; gap: 20px; margin-bottom: 30px;">
        <div style="flex: 1; background-color: #D2E0D3; padding: 25px;">
            <div style="font-size: 14px; color: #3C3C3C; font-weight: bold; margin-bottom: 10px;">
                TOTAL RAK
            </div>
            <div style="font-size: 32px; color: #3C3C3C; font-weight: bold;">
                3 rak
            </div>
        </div>
        <div style="flex: 1; background-color: #F0DDD6; padding: 25px;">
            <div style="font-size: 14px; color: #3C3C3C; font-weight: bold; margin-bottom: 10px;">
                TOTAL ITEM
            </div>
            <div style="font-size: 32px; color: #3C3C3C; font-weight: bold;">
                21 item
            </div>
        </div>
        <div style="flex: 1; background-color: #F2C3B9; padding: 25px;">
            <div style="font-size: 14px; color: #3C3C3C; font-weight: bold; margin-bottom: 10px;">
                TOTAL NOMINAL
            </div>
            <div style="font-size: 32px; color: #3C3C3C; font-weight: bold;">
                -Rp 34.556
            </div>
        </div>
    </div>

    <div style="background-color: #FFFFFF; padding: 25px; margin-bottom: 20px;">
        <div style="font-size: 18px; color: #3C3C3C; font-weight: bold; margin-bottom: 15px;">
            RINGKASAN PERIODE
        </div>
        <div style="font-size: 16px; color: #3C3C3C; line-height: 1.6;">
            Tanggal: 2026-10-10<br>
            Total Rak: 3 rak<br>
            Nominal SO: -Rp 34.556<br>
            Sales Periode: Rp 10<br>
            BTSB (0,15%): Rp 0<br>
            Keterangan: OVER
        </div>
    </div>

    <div style="background-color: #FFFFFF; padding: 25px;">
        <div style="font-size: 18px; color: #3C3C3C; font-weight: bold; margin-bottom: 15px;">
            INSIGHT
        </div>
        <div style="font-size: 16px; color: #3C3C3C; line-height: 1.6;">
            Total SO: 3 rak dengan nominal -Rp 34.556. Sales periode: Rp 10.
            BTSB (0,15%): Rp 0. Rak penyumbang minus terbesar: S14 (-Rp 24.785)
            oleh PIC REZA. Status: OVER - selisih melebihi batas BTSB.
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
        
        st.info(f"✅ Render: `{type(_image)}`")
        
        _tmp_path = os.path.join(tempfile.gettempdir(), "test_infografis.png")
        _image.save(_tmp_path)
        
        with open(_tmp_path, "rb") as _f:
            _img_bytes = _f.read()
        
        st.success(f"✅ Save: {len(_img_bytes):,} bytes")
        
        st.markdown("---")
        st.markdown("### 📸 Hasil")
        st.image(_img_bytes, caption="Hasil html2pic")
    
    except Exception as e:
        import traceback
        st.error(f"❌ Gagal:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")
