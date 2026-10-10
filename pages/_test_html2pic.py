"""
Test pictex Canvas — Konstruksi Infografis
============================================
Menggunakan pictex langsung (bukan html2pic) untuk render PNG.
"""
import streamlit as st
import os
import tempfile
from datetime import datetime


st.set_page_config(page_title="Test pictex", page_icon="🧪")
st.title("Test pictex Canvas — Infografis")


# =========================================================
# DATA DUMMY
# =========================================================
_data = {
    "periode": "2026-10-10 s/d 2026-10-10",
    "total_rak": 3,
    "total_item": 21,
    "total_nominal": -34556,
    "sales_periode": 10,
    "btsb": 0,
    "status": "OVER",
    "insight": (
        "Total SO: 3 rak dengan nominal -Rp 34.556. Sales periode: Rp 10. "
        "BTSB (0,15%): Rp 0. Rak penyumbang minus terbesar: S14 (-Rp 24.785) "
        "oleh PIC REZA. Status: OVER - selisih melebihi batas BTSB, perlu perhatian."
    ),
    "list_rak": [
        {"rak_id": "S14", "nama": "PERSONAL & TOOTH CARE 4", "pic": "REZA", "nominal": -24785},
        {"rak_id": "S15", "nama": "PERSONAL & TOOTH CARE 5", "pic": "KUSDEWI", "nominal": -10273},
        {"rak_id": "800", "nama": "RAK CUSTOM", "pic": "REZA", "nominal": 503},
    ],
}


# =========================================================
# HELPER
# =========================================================
def _fmt_rp(val):
    _n = int(round(float(val)))
    _sign = "+" if _n >= 0 else "-"
    return f"{_sign}Rp {abs(_n):,}".replace(",", ".")


def _fmt_rp_no_sign(val):
    _n = int(round(float(val)))
    return f"Rp {abs(_n):,}".replace(",", ".")


# =========================================================
# KONSTRUKSI INFOGRAFIS
# =========================================================
def _build_infografis(data):
    from pictex import Canvas, Row, Column, Text

    # === CANVAS ===
    canvas = (
        Canvas()
        .size(width=1080, height=1350)
        .background_color("#F0EEEA")
        .padding(40)
    )

    # === HEADER BAND ===
    header = (
        Column(
            Text("ANALISIS GAMBARAN SO").font_size(36).color("#FFFFFF").font_weight("bold"),
            Text(f"Toko C383 - Karang Satria - {data['periode']}").font_size(18).color("#F0EEEA"),
        )
        .padding(30)
        .background_color("#97B3AE")
        .border_radius(16)
        .gap(10)
    )

    # === KPI CARDS ===
    kpi_row = Row(
        Column(
            Text("TOTAL RAK").font_size(14).color("#3C3C3C").font_weight("bold"),
            Text(f"{data['total_rak']} rak").font_size(32).color("#3C3C3C").font_weight("bold"),
        ).flex_grow(1).padding(25).background_color("#D2E0D3").border_radius(12).gap(6),

        Column(
            Text("TOTAL ITEM").font_size(14).color("#3C3C3C").font_weight("bold"),
            Text(f"{data['total_item']} item").font_size(32).color("#3C3C3C").font_weight("bold"),
        ).flex_grow(1).padding(25).background_color("#F0DDD6").border_radius(12).gap(6),

        Column(
            Text("TOTAL NOMINAL").font_size(14).color("#3C3C3C").font_weight("bold"),
            Text(_fmt_rp(data['total_nominal'])).font_size(32).color("#3C3C3C").font_weight("bold"),
        ).flex_grow(1).padding(25).background_color("#F2C3B9").border_radius(12).gap(6),
    ).gap(20)

    # === RINGKASAN PERIODE ===
    ringkasan = (
        Column(
            Text("RINGKASAN PERIODE").font_size(18).color("#3C3C3C").font_weight("bold"),
            Text(f"Tanggal: {data['periode']}").font_size(16).color("#3C3C3C"),
            Text(f"Total Rak di-SO: {data['total_rak']} rak").font_size(16).color("#3C3C3C"),
            Text(f"Nominal SO: {_fmt_rp(data['total_nominal'])}").font_size(16).color("#3C3C3C"),
            Text(f"Sales Periode: {_fmt_rp_no_sign(data['sales_periode'])}").font_size(16).color("#3C3C3C"),
            Text(f"BTSB (0,15%): {_fmt_rp_no_sign(data['btsb'])}").font_size(16).color("#3C3C3C"),
            Text(f"Keterangan: {data['status']}").font_size(16).color("#C83232").font_weight("bold"),
        )
        .padding(25)
        .background_color("#FFFFFF")
        .border_radius(12)
        .gap(10)
    )

    # === INSIGHT ===
    insight = (
        Column(
            Text("INSIGHT").font_size(18).color("#3C3C3C").font_weight("bold"),
            Text(data["insight"]).font_size(14).color("#3C3C3C"),
        )
        .padding(25)
        .background_color("#F0EEEA")
        .border_radius(12)
        .gap(10)
    )

    # === TABEL RAK ===
    _header_cells = Row(
        Text("RAK").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).flex_grow(1),
        Text("NAMA RAK").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).flex_grow(3),
        Text("PIC").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).flex_grow(2),
        Text("SELISIH").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).flex_grow(2),
    ).background_color("#97B3AE").border_radius(8)

    _rows = [_header_cells]
    for _r in data["list_rak"]:
        _color = "#C83232" if _r["nominal"] < 0 else "#329632"
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(14).color("#3C3C3C").padding(12).flex_grow(1),
                Text(_r["nama"]).font_size(14).color("#3C3C3C").padding(12).flex_grow(3),
                Text(_r["pic"]).font_size(14).color("#3C3C3C").padding(12).flex_grow(2),
                Text(_fmt_rp(_r["nominal"])).font_size(14).color(_color).font_weight("bold").padding(12).flex_grow(2),
            )
        )

    tabel_rak = Column(*_rows).background_color("#FFFFFF").border_radius(8).gap(2)

    # === SUSUN LAYOUT UTAMA ===
    layout = Column(
        header,
        kpi_row,
        ringkasan,
        insight,
        tabel_rak,
    ).gap(20)

    return canvas.render(layout)


# =========================================================
# RENDER
# =========================================================
if st.button("Test Render Infografis", type="primary"):
    try:
        _image = _build_infografis(_data)

        _tmp_path = os.path.join(tempfile.gettempdir(), "test_infografis.png")
        _image.save(_tmp_path)

        with open(_tmp_path, "rb") as _f:
            _img_bytes = _f.read()

        st.success(f"✅ Save: {len(_img_bytes):,} bytes")

        st.markdown("---")
        st.markdown("### 📸 Hasil")
        st.image(_img_bytes, caption="Hasil pictex")

    except Exception as e:
        import traceback
        st.error(f"❌ Gagal:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")
