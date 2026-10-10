import streamlit as st
import io

st.title("Test html2pic")

_html = """
<html>
<body style="font-family: Arial; padding: 20px; background: #F0EEEA;">
    <div style="background: #97B3AE; color: white; padding: 20px; border-radius: 12px;">
        <h1 style="margin: 0;">TEST HEADER</h1>
        <p>Toko C383 — 10/10/2026</p>
    </div>
    <div style="display: flex; gap: 12px; margin-top: 20px;">
        <div style="flex: 1; background: #D2E0D3; padding: 15px; border-radius: 10px;">
            <small>TOTAL RAK</small>
            <h2 style="margin: 5px 0;">3 rak</h2>
        </div>
        <div style="flex: 1; background: #F0DDD6; padding: 15px; border-radius: 10px;">
            <small>TOTAL ITEM</small>
            <h2 style="margin: 5px 0;">21 item</h2>
        </div>
        <div style="flex: 1; background: #F2C3B9; padding: 15px; border-radius: 10px;">
            <small>TOTAL NOMINAL</small>
            <h2 style="margin: 5px 0;">-Rp 34.556</h2>
        </div>
    </div>
</body>
</html>
"""

if st.button("Test Render"):
    try:
        from html2pic import Html2Pic
        _render = Html2Pic(_html)
        _image = _render.render()
        
        _buf = io.BytesIO()
        _image.save(_buf, format="PNG")
        _buf.seek(0)
        
        st.image(_buf, caption="Hasil html2pic")
        st.success("✅ html2pic WORKS!")
    except Exception as e:
        import traceback
        st.error(f"❌ html2pic GAGAL:\n\n```\n{str(e)}\n\n{traceback.format_exc()}\n```")
