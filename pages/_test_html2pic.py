"""
Test pictex Canvas — bukan html2pic.
"""
import streamlit as st
import os
import tempfile


st.set_page_config(page_title="Test pictex", page_icon="🧪")
st.title("Test pictex Canvas")


if st.button("Test Render", type="primary"):
    try:
        from pictex import Canvas, Column, Row, Text
        from pictex import LinearGradient

        # === BIKIN CANVAS ===
        _canvas = (
            Canvas()
            .size(width=1080, height=800)
            .padding(40)
            .background_color("#F0EEEA")
        )

        # === HEADER BAND ===
        _header = (
            Column()
            .padding(30)
            .background_color("#97B3AE")
            .border_radius(16)
            .gap(10)
        )
        _header.add(
            Text("ANALISIS GAMBARAN SO").font_size(36).color("#FFFFFF").font_weight("bold"),
            Text("Toko C383 - Karang Satria - 10/10/2026").font_size(18).color("#F0EEEA"),
        )

        # === KPI CARDS ===
        _kpi_row = Row().gap(20)
        _kpi_row.add(
            Column().flex_grow(1).padding(25).background_color("#D2E0D3").border_radius(12).add(
                Text("TOTAL RAK").font_size(14).color("#3C3C3C").font_weight("bold"),
                Text("3 rak").font_size(32).color("#3C3C3C").font_weight("bold"),
            ),
            Column().flex_grow(1).padding(25).background_color("#F0DDD6").border_radius(12).add(
                Text("TOTAL ITEM").font_size(14).color("#3C3C3C").font_weight("bold"),
                Text("21 item").font_size(32).color("#3C3C3C").font_weight("bold"),
            ),
            Column().flex_grow(1).padding(25).background_color("#F2C3B9").border_radius(12).add(
                Text("TOTAL NOMINAL").font_size(14).color("#3C3C3C").font_weight("bold"),
                Text("-Rp 34.556").font_size(32).color("#3C3C3C").font_weight("bold"),
            ),
        )

        # === RINGKASAN ===
        _ringkasan = (
            Column()
            .padding(25)
            .background_color("#FFFFFF")
            .border_radius(12)
            .gap(10)
        )
        _ringkasan.add(
            Text("RINGKASAN PERIODE").font_size(18).color("#3C3C3C").font_weight("bold"),
            Text("Tanggal: 2026-10-10").font_size(16).color("#3C3C3C"),
            Text("Total Rak: 3 rak").font_size(16).color("#3C3C3C"),
            Text("Nominal SO: -Rp 34.556").font_size(16).color("#3C3C3C"),
            Text("Status: OVER").font_size(16).color("#C83232").font_weight("bold"),
        )

        # === SUSUN LAYOUT ===
        _main = Column().gap(20)
        _main.add(_header, _kpi_row, _ringkasan)

        # === RENDER ===
        _image = _canvas.render(_main)

        _tmp_path = os.path.join(tempfile.gettempdir(), "test_pictex.png")
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
