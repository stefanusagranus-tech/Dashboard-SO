"""
Test html2pic — Eksperimen CSS layout infografis.
"""
import streamlit as st
import io
import os
import tempfile


st.set_page_config(page_title="Test html2pic", page_icon="🧪")
st.title("Test html2pic - Eksperimen Infografis")


# =========================================================
# HTML INFOGRAFIS
# =========================================================
_html = """
<html>
<head>
<style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: Arial, sans-serif;
        background: #F0EEEA;
        width: 1080px;
        padding: 40px;
    }
    .header {
        background: #97B3AE;
        color: #FFFFFF;
        padding: 30px 40px;
        border-radius: 16px;
        margin-bottom: 30px;
    }
    .header h1 {
        font-size: 36px;
        margin-bottom: 8px;
        color: #FFFFFF;
    }
    .header p {
        font-size: 18px;
        color: #F0EEEA;
    }
    .kpi-row {
        display: flex;
        gap: 20px;
        margin-bottom: 30px;
    }
    .kpi-card {
        flex: 1;
        padding: 25px;
        border-radius: 12px;
    }
    .kpi-label {
        font-size: 14px;
        color: #3C3C3C;
        margin-bottom: 10px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    .kpi-value {
        font-size: 32px;
        color: #3C3C3C;
        font-weight: bold;
    }
    .kpi-1 { background: #D2E0D3; }
    .kpi-2 { background: #F0DDD6; }
    .kpi-3 { background: #F2C3B9; }
    .section {
        background: #FFFFFF;
        padding: 25px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .section-title {
        font-size: 18px;
        font-weight: bold;
        color: #3C3C3C;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #97B3AE;
    }
    .section-content {
        font-size: 16px;
        color: #3C3C3C;
        line-height: 1.6;
    }
    .footer {
        text-align: center;
        font-size: 12px;
        color: #A89B8E;
        margin-top: 30px;
        font-style: italic;
    }
</style>
</head>
<body>

    <!-- HEADER -->
    <div class="header">
        <h1>ANALISIS GAMBARAN SO</h1>
        <p>Toko C383 - Karang Satria - 10/10/2026</p>
    </div>

    <!-- KPI CARDS -->
    <div class="kpi-row">
        <div class="kpi-card kpi-1">
            <div class="kpi-label">TOTAL RAK</div>
            <div class="kpi-value">3 rak</div>
        </div>
        <div class="kpi-card kpi-2">
            <div class="kpi-label">TOTAL ITEM</div>
            <div class="kpi-value">21 item</div>
        </div>
        <div class="kpi-card kpi-3">
            <div class="kpi-label">TOTAL NOMINAL</div>
            <div class="kpi-value">-Rp 34.556</div>
        </div>
    </div>

    <!-- RINGKASAN -->
    <div class="section">
        <div class="section-title">RINGKASAN PERIODE</div>
        <div class="section-content">
            Tanggal: 2026-10-10<br>
            Total Rak di-SO: 3 rak<br>
            Nominal SO: -Rp 34.556<br>
            Sales Periode: Rp 10<br>
            BTSB (0,15%): Rp 0<br>
            Keterangan: <b style="color: #C83232;">OVER</b>
        </div>
    </div>

    <!-- INSIGHT -->
    <div class="section">
        <div class="section-title">INSIGHT</div>
        <div class="section-content" style="font-style: italic;">
            Total SO: 3 rak dengan nominal -Rp 34.556. Sales periode: Rp 10.
            BTSB (0,15%): Rp 0. Rak penyumbang minus terbesar: S14 (-Rp 24.785)
            oleh PIC REZA. Status: OVER - selisih melebihi batas BTSB, perlu perhatian.
        </div>
    </div>

    <!-- FOOTER -->
    <div class="footer">
        Dokumen ini di-generate otomatis oleh Yui - Dashboard SO Toko C383
    </div>

</body>
</html>
"""


# =========================================================
# RENDER
# =========================================================
if st.button("Test Render", type="primary"):
    try:
        from html2pic import Html2Pic
        
        _render = Html2Pic(_html)
        _image = _render.render()
        
        st.info(f"✅ Render berhasil! Tipe: `{type(_image)}`")
        
        _tmp_path = os.path.join(tempfile.gettempdir(), "test_infografis.png")
        _image.save(_tmp_path)
        
        with open(_tmp_path, "rb") as _f:
            _img_bytes = _f.read()
        
        st.success(f"✅ Save berhasil! Ukuran: {len(_img_bytes):,} bytes")
        
        st.markdown("---")
        st.markdown("### 📸 Hasil")
        st.image(_img_bytes, caption="Hasil html2pic")
    
    except Exception as e:
        import traceback
        st.error(f"❌ Gagal:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")
