"""
AI Chat Yui — Pembantu Input SO (AI-2)
========================================
Halaman chat fullscreen untuk Yui.
Persona: Rekan kerja profesional, teliti, natural.

Fitur:
- Chat natural + memory persistent
- Upload file (PDF/foto/Excel) → Yui baca
- Parse natural language SO
- Validasi + konfirmasi sebelum save
- Auto-save ke Supabase
"""

import streamlit as st
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from themes.theme_loader import (
    render_theme,
    render_theme_animations,
    get_theme_by_month,
)

# =========================================================================
# KONFIGURASI
# =========================================================================
st.set_page_config(
    page_title="Yui — Input SO",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)


# =========================================================================
# IMPORT MODULES
# =========================================================================
try:
    from modules.ai_so_input import (
        parse_natural_language,
        parse_file_text,
        yui_chat,
        validate_so_data,
        generate_so_rekap,
    )
    from modules.file_reader import read_file, detect_file_type
    from modules.chat_memory import (
        save_message,
        load_messages,
        get_or_create_session_id,
        clear_session,
    )
    from modules.data_loader import load_rak_master
    from modules.master_shift_handler import load_personil_master
    from modules.input_handler import save_input_harian
    _YUI_OK = True
except ImportError as e:
    _YUI_OK = False
    _import_error = str(e)


# =========================================================================
# CSS — ROOM CHAT YUI
# =========================================================================
def inject_yui_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        .main .block-container {
            max-width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1rem !important;
        }

        .stApp, .stApp * {
            color: #F5E6D3 !important;
        }

        .stApp button {
            color: inherit !important;
        }

        .stApp textarea,
        .stApp input,
        .stApp [contenteditable="true"] {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
            caret-color: #7FB99B !important;
        }

        .stApp textarea::placeholder,
        .stApp input::placeholder {
            color: rgba(245, 230, 211, 0.5) !important;
        }

        /* Chat bubble */
        [data-testid="stChatMessage"] {
            padding: 0.85rem 1.2rem !important;
            margin-bottom: 0.6rem !important;
            border-radius: 16px !important;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] strong,
        [data-testid="stChatMessage"] em {
            color: #F5E6D3 !important;
        }

        /* USER bubble — mint */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, rgba(127, 185, 155, 0.25), rgba(232, 177, 137, 0.15)) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
            margin-left: 20% !important;
        }

        /* YUI bubble — deep purple */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.85), rgba(76, 29, 149, 0.65)) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.5) !important;
            margin-right: 20% !important;
        }

        [data-testid="chatAvatarIcon-assistant"] {
            background: linear-gradient(135deg, #7FB99B, #4C9B7F) !important;
        }

        /* Chat input */
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.6) !important;
            border-radius: 16px !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
        }

        [data-testid="stChatInputContainer"] textarea,
        [data-testid="stChatInputContainer"] input {
            color: #F5E6D3 !important;
            background: transparent !important;
        }

        [data-testid="stChatInputContainer"] textarea::placeholder {
            color: rgba(245, 230, 211, 0.5) !important;
        }

        [data-testid="stChatInputContainer"] button {
            background: linear-gradient(135deg, #7FB99B, #4C9B7F) !important;
            border: none !important;
            color: #fff !important;
        }

        /* Memory info bar */
        .memory-info {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #7FB99B;
            border-radius: 8px;
            padding: 8px 14px;
            margin-bottom: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #A89B8E;
        }

        /* Preview card */
        .preview-card {
            background: linear-gradient(135deg, rgba(28, 16, 48, 0.95), rgba(45, 25, 75, 0.9));
            border: 1px solid rgba(127, 185, 155, 0.4);
            border-left: 4px solid #7FB99B;
            border-radius: 12px;
            padding: 16px 20px;
            margin: 12px 0;
        }

        .preview-card .preview-title {
            font-family: 'Cinzel', serif;
            font-size: 14px;
            color: #7FB99B;
            letter-spacing: 2px;
            margin-bottom: 10px;
            text-transform: uppercase;
        }

        /* Warning card */
        .warning-card {
            background: linear-gradient(135deg, rgba(251, 191, 36, 0.10), rgba(245, 158, 11, 0.15));
            border: 1px solid #fbbf24;
            border-left: 4px solid #fbbf24;
            border-radius: 10px;
            padding: 12px 16px;
            margin: 8px 0;
            font-family: 'Quicksand', sans-serif;
            font-size: 12px;
            color: #FDE68A;
        }

        /* PIC required banner */
        .pic-required {
            background: linear-gradient(135deg, rgba(232, 139, 139, 0.15), rgba(220, 38, 38, 0.10));
            border: 1.5px solid #E88B8B;
            border-left: 4px solid #E88B8B;
            border-radius: 10px;
            padding: 14px 18px;
            margin: 12px 0;
        }

        .pic-required .pic-title {
            font-family: 'Cinzel', serif;
            font-size: 13px;
            color: #E88B8B;
            letter-spacing: 2px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }

        .pic-required .pic-sub {
            font-family: 'Quicksand', sans-serif;
            font-size: 11px;
            color: #F5E6D3;
        }

        /* File info card */
        .file-info {
            background: rgba(20, 12, 35, 0.95);
            border: 1px solid rgba(168, 85, 247, 0.3);
            border-radius: 10px;
            padding: 10px 14px;
            margin: 8px 0;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            color: #A89B8E;
        }

        div[data-testid="stHorizontalBlock"] button {
            border-radius: 12px !important;
            font-weight: 700 !important;
        }
    </style>
    """, unsafe_allow_html=True)


inject_yui_css()


# =========================================================================
# GUARD — Cek import
# =========================================================================
if not _YUI_OK:
    st.error(f"❌ Gagal import module: {_import_error}")
    st.info("💡 Pastikan `modules/ai_so_input.py` + `modules/file_reader.py` + `modules/chat_memory.py` udah ada.")
    st.stop()


# =========================================================================
# LOAD MASTER DATA
# =========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def _load_master():
    _rak_df = load_rak_master()
    _personil_df = load_personil_master(only_active=True)
    return _rak_df, _personil_df


_rak_df, _personil_df = _load_master()
_personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []
_rak_list = _rak_df["rak_id"].tolist() if not _rak_df.empty else []


# =========================================================================
# HEADER
# =========================================================================
def render_yui_header():
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")

    _col_back, _col_title, _col_status = st.columns([1, 3, 1])

    with _col_back:
        if st.button("← Dashboard", key="btn_back_yui", width="stretch"):
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.warning("⚠️ Gagal pindah halaman.")

    with _col_title:
        st.markdown(
            "<div style='text-align: center;'>"
            "<div style='font-family: Cinzel, serif; font-size: 22px; "
            "font-weight: 900; color: #7FB99B; letter-spacing: 2px; "
            "text-shadow: 0 0 15px rgba(127, 185, 155, 0.6);'>"
            "📦 YUI 📦</div>"
            "<div style='font-family: Quicksand, sans-serif; font-size: 10px; "
            "color: #E8B189; letter-spacing: 1.5px; margin-top: 2px;'>"
            "Data Entry Specialist — Input SO Toko C383</div>"
            "</div>",
            unsafe_allow_html=True,
        )

    with _col_status:
        st.markdown(
            f"<div style='text-align: right; font-family: JetBrains Mono, monospace; "
            f"font-size: 10px; color: #7FB99B; padding-top: 8px;'>"
            f"🕐 {_time_str} WIB<br>● ONLINE</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")


render_yui_header()


# =========================================================================
# SESSION STATE + MEMORY
# =========================================================================
_session_id = get_or_create_session_id("yui")

# Init history — LOAD DARI SUPABASE
if "yui_history" not in st.session_state:
    with st.spinner("⏳ Load chat history..."):
        _saved = load_messages("yui", _session_id, limit=100)

    st.session_state["yui_history"] = [
        {"role": _m.get("role", "user"), "content": _m.get("content", "")}
        for _m in _saved
    ]

if "yui_pending_data" not in st.session_state:
    st.session_state["yui_pending_data"] = None

if "yui_uploaded_file_info" not in st.session_state:
    st.session_state["yui_uploaded_file_info"] = None

if "yui_last_saved" not in st.session_state:
    st.session_state["yui_last_saved"] = None


# =========================================================================
# WELCOME MESSAGE (kalau history kosong)
# =========================================================================
if not st.session_state["yui_history"]:
    _welcome = (
        "📦 **Halo Bos!** Aku Yui, siap bantu urusan input SO.\n\n"
        "Ada 3 cara buat aku bantu:\n"
        "1. **Ketik langsung** — `Q51 minus 28rb, PIC Pandu`\n"
        "2. **Upload file** — PDF/foto/Excel laporan SO\n"
        "3. **Chat aja** — kalau ada yang perlu ditanya\n\n"
        "Gas aja Bos, aku standby 👌"
    )

    _entry = {"role": "assistant", "content": _welcome}
    st.session_state["yui_history"].append(_entry)
    save_message("yui", _session_id, "assistant", _welcome)


# =========================================================================
# NOTIFIKASI SUKSES
# =========================================================================
if st.session_state["yui_last_saved"]:
    st.success(st.session_state["yui_last_saved"])
    st.session_state["yui_last_saved"] = None


# =========================================================================
# MEMORY INFO BAR
# =========================================================================
_total_msg = len(st.session_state["yui_history"])
st.markdown(
    f"<div class='memory-info'>"
    f"🧠 <b>Memory Aktif</b> | "
    f"Session: <code style='color: #E8B189;'>{_session_id[-15:]}</code> | "
    f"Total: <b style='color: #7FB99B;'>{_total_msg}</b> pesan"
    f"</div>",
    unsafe_allow_html=True,
)


# =========================================================================
# TOOLBAR
# =========================================================================
st.markdown("#### ⚡ Aksi Cepat")
_col_t1, _col_t2, _col_t3, _col_t4 = st.columns(4)

with _col_t1:
    if st.button("📎 Upload File", width="stretch", key="btn_yui_upload"):
        st.session_state["yui_show_upload"] = True

with _col_t2:
    if st.button("📊 Rekap SO", width="stretch", key="btn_yui_rekap"):
        st.session_state["yui_preset"] = "Rekap SO aku dong hari ini"

with _col_t3:
    if st.button("📄 Generate PDF", width="stretch", key="btn_yui_pdf"):
        st.session_state["yui_preset"] = "Generate PDF SO hari ini"

with _col_t4:
    if st.button("🗑️ Reset", width="stretch", key="btn_yui_reset"):
        clear_session("yui", _session_id)
        st.session_state["yui_history"] = []
        st.session_state["yui_pending_data"] = None
        st.rerun()

st.markdown("---")


# =========================================================================
# DIALOG UPLOAD FILE
# =========================================================================
@st.dialog("📎 Upload File SO", width="large")
def _dialog_upload_file():
    st.markdown(
        "<div style='font-family: Quicksand, sans-serif; font-size: 12px; "
        "color: #A89B8E; margin-bottom: 12px;'>"
        "Upload file laporan SO (PDF, foto, Excel, CSV). Yui bakal baca otomatis."
        "</div>",
        unsafe_allow_html=True,
    )

    _uploaded = st.file_uploader(
        "Pilih file",
        type=["pdf", "png", "jpg", "jpeg", "webp", "xlsx", "xls", "csv"],
        key="yui_file_upload",
        label_visibility="collapsed",
    )

    # Konteks tambahan (opsional)
    with st.expander("➕ Tambah Konteks (Opsional)", expanded=False):
        _col_c1, _col_c2 = st.columns(2)

        with _col_c1:
            _tgl_ctx = st.date_input(
                "Tanggal SO",
                value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
                key="yui_file_tgl",
            )

        with _col_c2:
            _rak_ctx = st.text_input(
                "Kode Rak (kalau gak ada di file)",
                placeholder="Contoh: Q51",
                key="yui_file_rak",
            )

    st.markdown("")

    _col_process, _col_cancel = st.columns(2)

    with _col_process:
        if st.button(
            "🔍 PROSES FILE",
            width="stretch",
            type="primary",
            key="btn_yui_process_file",
            disabled=(not _uploaded),
        ):
            if not _uploaded:
                st.error("⚠️ Pilih file dulu Bos")
                return

            _file_name = _uploaded.name
            _file_bytes = _uploaded.getvalue()
            _ftype = detect_file_type(_file_name)

            # Simpan ke session state buat process
            st.session_state["yui_file_to_process"] = {
                "name": _file_name,
                "bytes": _file_bytes,
                "type": _ftype,
                "tanggal": _tgl_ctx.isoformat() if _tgl_ctx else None,
                "rak_id": _rak_ctx.strip().upper() if _rak_ctx else None,
            }
            st.session_state["yui_show_upload"] = False
            st.rerun()

    with _col_cancel:
        if st.button("❌ BATAL", width="stretch", key="btn_yui_cancel_upload"):
            st.session_state["yui_show_upload"] = False
            st.rerun()


# Show dialog kalau flag aktif
if st.session_state.get("yui_show_upload"):
    _dialog_upload_file()
# =========================================================================
# RENDER CHAT HISTORY
# =========================================================================
st.markdown("#### 💬 Percakapan")

for _idx, _msg in enumerate(st.session_state["yui_history"]):
    _role = _msg.get("role", "user")
    _content = _msg.get("content", "")

    with st.chat_message(_role, avatar="👤" if _role == "user" else "📦"):
        st.markdown(_content)


# =========================================================================
# PROCESS FILE (kalau ada yang perlu diproses)
# =========================================================================
if st.session_state.get("yui_file_to_process"):
    _file_data = st.session_state["yui_file_to_process"]
    _file_name = _file_data["name"]
    _file_bytes = _file_data["bytes"]
    _file_type = _file_data["type"]
    _tgl_ctx = _file_data.get("tanggal")
    _rak_ctx = _file_data.get("rak_id")

    # Show "sedang proses"
    with st.chat_message("assistant", avatar="📦"):
        _processing_msg = f"📎 Aku baca file **{_file_name}** dulu ya Bos... ⏳"
        st.markdown(_processing_msg)

    with st.spinner(f"📦 Yui baca file {_file_name}..."):
        # Step 1: Read file
        _read_result = read_file(
            _file_bytes,
            _file_name,
            bulan=datetime.now(ZoneInfo("Asia/Jakarta")).month,
            tahun=datetime.now(ZoneInfo("Asia/Jakarta")).year,
        )

    if not _read_result.get("success"):
        _err_msg = f"❌ Waduh, aku gagal baca file-nya Bos.\n\n**Error:** {_read_result.get('error', 'Unknown')}"
        with st.chat_message("assistant", avatar="📦"):
            st.markdown(_err_msg)

        st.session_state["yui_history"].append({"role": "assistant", "content": _err_msg})
        save_message("yui", _session_id, "assistant", _err_msg)
        st.session_state["yui_file_to_process"] = None
        st.rerun()

    # Step 2: Parse dengan Yui
    with st.spinner("📦 Yui olah data file..."):
        _context = {
            "tanggal": _tgl_ctx,
            "rak_id": _rak_ctx,
            "pic": None,
        }

        _parse_result = parse_file_text(
            _read_result.get("text", ""),
            file_type=_read_result.get("type", "unknown"),
            context=_context,
        )

    # Step 3: Handle hasil parsing
    if not _parse_result.get("success"):
        _fail_msg = f"❌ Aku gagal extract data SO dari file ini Bos.\n\n{_parse_result.get('warnings', [''])[0]}"
        with st.chat_message("assistant", avatar="📦"):
            st.markdown(_fail_msg)

        st.session_state["yui_history"].append({"role": "assistant", "content": _fail_msg})
        save_message("yui", _session_id, "assistant", _fail_msg)
        st.session_state["yui_file_to_process"] = None
        st.rerun()

    # Step 4: Preview data
    _data = _parse_result.get("data", {}) or {}
    _missing = _parse_result.get("missing", [])
    _warnings = _parse_result.get("warnings", [])

    # Normalize
    _tanggal = _data.get("tanggal") or _tgl_ctx or datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()
    _rak_id = _data.get("rak_id") or _rak_ctx or None
    _pic = _data.get("pic")
    _items = _data.get("items", [])
    _total_nominal = _data.get("total_nominal", 0)

    with st.chat_message("assistant", avatar="📦"):
        _preview_msg = f"✅ File **{_file_name}** berhasil aku baca Bos.\n\n"
        _preview_msg += f"📊 **Ringkasan:**\n"
        _preview_msg += f"- 📅 Tanggal: **{_tanggal}**\n"
        _preview_msg += f"- 🏪 Rak: **{_rak_id if _rak_id else '❓ Belum ada'}**\n"
        _preview_msg += f"- 👤 PIC: **{_pic if _pic else '❓ Belum ada'}**\n"
        _preview_msg += f"- 📦 Jumlah produk: **{len(_items)}**\n"

        if _total_nominal:
            _preview_msg += f"- 💰 Total nominal: **Rp {int(_total_nominal):,}**".replace(",", ".")

        if _warnings:
            _preview_msg += "\n\n⚠️ **Catatan:**\n"
            for _w in _warnings:
                _preview_msg += f"- {_w}\n"

        st.markdown(_preview_msg)

    # Save preview ke history
    st.session_state["yui_history"].append({"role": "assistant", "content": _preview_msg})
    save_message("yui", _session_id, "assistant", _preview_msg)

    # Step 5: Cek data yang kurang
    _missing_fields = []
    if not _rak_id:
        _missing_fields.append("rak_id")
    if not _pic:
        _missing_fields.append("pic")

    if _missing_fields:
        # Set pending data
        st.session_state["yui_pending_data"] = {
            "source": "file",
            "file_name": _file_name,
            "tanggal": _tanggal,
            "rak_id": _rak_id,
            "pic": _pic,
            "items": _items,
            "total_nominal": _total_nominal,
            "missing": _missing_fields,
        }
        st.session_state["yui_file_to_process"] = None
        st.rerun()
    else:
        # Data lengkap — langsung tampil preview + konfirmasi save
        st.session_state["yui_pending_data"] = {
            "source": "file",
            "file_name": _file_name,
            "tanggal": _tanggal,
            "rak_id": _rak_id,
            "pic": _pic,
            "items": _items,
            "total_nominal": _total_nominal,
            "missing": [],
        }
        st.session_state["yui_file_to_process"] = None
        st.rerun()


# =========================================================================
# PENDING DATA — TANYA FIELD YANG KURANG + PREVIEW + SAVE
# =========================================================================
if st.session_state.get("yui_pending_data"):
    _pending = st.session_state["yui_pending_data"]
    _missing = _pending.get("missing", [])

    st.markdown("---")

    # === ASK MISSING FIELDS ===
    if _missing:
        st.markdown("#### ❓ Data Perlu Dilengkapi")
        st.markdown(
            f"<div class='pic-required'>"
            f"<div class='pic-title'>📝 DATA BELUM LENGKAP</div>"
            f"<div class='pic-sub'>Aku butuh info berikut buat lanjut simpan:</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        with st.form("yui_missing_form", clear_on_submit=False):
            _input_values = {}

            if "rak_id" in _missing:
                if _rak_list:
                    _input_values["rak_id"] = st.selectbox(
                        "🏪 Kode Rak",
                        options=_rak_list,
                        key="yui_missing_rak",
                    )
                else:
                    _input_values["rak_id"] = st.text_input(
                        "🏪 Kode Rak",
                        placeholder="Contoh: Q51",
                        key="yui_missing_rak_manual",
                    )

            if "pic" in _missing:
                if _personil_list:
                    _input_values["pic"] = st.selectbox(
                        "👤 PIC (Nama)",
                        options=_personil_list,
                        key="yui_missing_pic",
                    )
                else:
                    _input_values["pic"] = st.text_input(
                        "👤 PIC (Nama)",
                        placeholder="Contoh: PANDU",
                        key="yui_missing_pic_manual",
                    )

            _col_submit, _col_cancel = st.columns(2)

            with _col_submit:
                _submit = st.form_submit_button(
                    "✅ LENGKAPI",
                    width="stretch",
                    type="primary",
                )

            with _col_cancel:
                _cancel = st.form_submit_button(
                    "❌ BATAL",
                    width="stretch",
                )

            if _submit:
                # Update pending data
                for _key, _val in _input_values.items():
                    st.session_state["yui_pending_data"][_key] = _val

                # Update missing — hapus yang udah diisi
                _new_missing = [
                    m for m in _missing
                    if not st.session_state["yui_pending_data"].get(m)
                ]
                st.session_state["yui_pending_data"]["missing"] = _new_missing
                st.rerun()

            if _cancel:
                _cancel_msg = "Oke Bos, aku batalkan file ini. Ada yang lain?"
                st.session_state["yui_history"].append({"role": "assistant", "content": _cancel_msg})
                save_message("yui", _session_id, "assistant", _cancel_msg)
                st.session_state["yui_pending_data"] = None
                st.rerun()

    # === PREVIEW + KONFIRMASI SAVE ===
    else:
        st.markdown("#### 📋 Preview Data SO")

        # Build preview table
        _preview_html = (
            f"<div class='preview-card'>"
            f"<div class='preview-title'>📦 DATA SIAP DISIMPAN</div>"
            f"<table class='so-table'>"
            f"<thead><tr>"
            f"<th>Field</th><th style='text-align: right;'>Nilai</th>"
            f"</tr></thead><tbody>"
            f"<tr><td class='rak-id'>📅 Tanggal</td>"
            f"<td style='text-align: right;'>{_pending.get('tanggal', '-')}</td></tr>"
            f"<tr><td class='rak-id'>🏪 Rak</td>"
            f"<td style='text-align: right;'>{_pending.get('rak_id', '-')}</td></tr>"
            f"<tr><td class='rak-id'>👤 PIC</td>"
            f"<td style='text-align: right;'>{_pending.get('pic', '-')}</td></tr>"
            f"<tr><td class='rak-id'>📦 Jumlah Item</td>"
            f"<td style='text-align: right;'>{len(_pending.get('items', []))}</td></tr>"
            f"</tbody></table>"
            f"</div>"
        )
        st.markdown(_preview_html, unsafe_allow_html=True)

        # Warning kalau ada
        _warnings_pending = _pending.get("warnings", [])
        if _warnings_pending:
            for _w in _warnings_pending:
                st.markdown(
                    f"<div class='warning-card'>⚠️ {_w}</div>",
                    unsafe_allow_html=True,
                )

        # Total nominal
        _total_nom = _pending.get("total_nominal", 0)
        _color_total = "#E88B8B" if _total_nom < 0 else "#7FB99B"

        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_color_total}; "
            f"text-align: right; margin-top: 12px;'>"
            f"<div class='label'>💰 TOTAL NOMINAL</div>"
            f"<div class='value' style='color: {_color_total};'>"
            f"{fmt_rp_signed(_total_nom) if 'fmt_rp_signed' in dir() else f'Rp {int(_total_nom):,}'.replace(',', '.')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Tombol aksi
        _col_save, _col_edit, _col_cancel = st.columns([2, 1, 1])

        with _col_save:
            if st.button(
                "💾 SIMPAN SEKARANG",
                width="stretch",
                type="primary",
                key="btn_yui_save_so",
            ):
                with st.spinner("📦 Aku simpan ya Bos..."):
                    # Prepare items
                    _items_to_save = []
                    for _item in _pending.get("items", []):
                        if "rak_id" not in _item:
                            _item["rak_id"] = _pending.get("rak_id")
                        _items_to_save.append(_item)

                    # Save via input_handler
                    try:
                        _save_ok, _save_msg, _save_detail = save_input_harian(
                            tanggal=datetime.strptime(_pending["tanggal"], "%Y-%m-%d").date(),
                            spd=0,
                            rak_items=_items_to_save,
                            keterangan=f"Input via Yui ({_pending.get('source', 'chat')})",
                            pic=_pending.get("pic", ""),
                            update_status_rak=True,
                        )

                        if _save_ok:
                            _success_msg = (
                                f"🎉 **Beres Bos!** Data SO udah aku simpan.\n\n"
                                f"📊 **Ringkasan:**\n"
                                f"- 📅 Tanggal: {_pending.get('tanggal')}\n"
                                f"- 🏪 Rak: **{_pending.get('rak_id')}**\n"
                                f"- 👤 PIC: {_pending.get('pic')}\n"
                                f"- 📦 Item: {len(_items_to_save)}\n"
                                f"- 💰 Nominal: Rp {int(_total_nom):,}".replace(",", ".") + "\n\n"
                                f"Cek di tab **📋 Preview** ya!"
                            )

                            st.session_state["yui_last_saved"] = _success_msg
                            st.session_state["yui_history"].append({
                                "role": "assistant",
                                "content": _success_msg,
                            })
                            save_message("yui", _session_id, "assistant", _success_msg)

                            st.session_state["yui_pending_data"] = None
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Gagal simpan: {_save_msg}")
                    except Exception as _e_save:
                        st.error(f"❌ Error: {str(_e_save)[:200]}")

        with _col_edit:
            if st.button(
                "✏️ EDIT",
                width="stretch",
                key="btn_yui_edit_pending",
            ):
                st.session_state["yui_pending_data"]["editing"] = True
                st.rerun()

        with _col_cancel:
            if st.button(
                "❌ BATAL",
                width="stretch",
                key="btn_yui_cancel_pending",
            ):
                _cancel_msg = "Oke Bos, aku batalkan input ini."
                st.session_state["yui_history"].append({
                    "role": "assistant",
                    "content": _cancel_msg,
                })
                save_message("yui", _session_id, "assistant", _cancel_msg)
                st.session_state["yui_pending_data"] = None
                st.rerun()


# =========================================================================
# CHAT INPUT
# =========================================================================
_preset = st.session_state.pop("yui_preset", "")
_user_msg = st.chat_input("Ketik atau upload file buat Yui...", key="yui_chat_input")

if _preset and not _user_msg:
    _user_msg = _preset

if _user_msg:
    # Simpan user message
    st.session_state["yui_history"].append({"role": "user", "content": _user_msg})
    save_message("yui", _session_id, "user", _user_msg)

    with st.chat_message("user", avatar="👤"):
        st.markdown(_user_msg)

    # Detect intent: parse SO atau chat biasa
    _user_lower = _user_msg.lower()
    _is_so_input = any(kw in _user_lower for kw in [
        "rak", "q51", "q52", "minus", "plus", "so ", "input so",
        "selisih", "pic ", "rp ", "-rp", "+rp", "ribu", "rb", "juta",
    ])

    with st.chat_message("assistant", avatar="📦"):
        with st.spinner("📦 Aku cek..."):
            if _is_so_input:
                # Coba parse natural language
                _parse_result = parse_natural_language(_user_msg, _rak_list[:100])

                if _parse_result.get("success") and _parse_result.get("data"):
                    _data = _parse_result["data"]
                    _items = _data.get("items", [])
                    _tanggal = _data.get("tanggal", datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat())
                    _warnings = _parse_result.get("warnings", [])

                    # Detect PIC & rak dari items
                    _first_item = _items[0] if _items else {}
                    _rak_id = _first_item.get("rak_id")
                    _pic = _first_item.get("pic")

                    # Cek missing
                    _missing = []
                    if not _rak_id:
                        _missing.append("rak_id")
                    if not _pic:
                        _missing.append("pic")

                    _total_nominal = sum(float(i.get("nominal_adjust", 0) or 0) for i in _items)

                    # Response Yui
                    _resp_text = (
                        f"📦 Oke Bos, aku catat ya:\n\n"
                        f"- 📅 Tanggal: **{_tanggal}**\n"
                    )
                    for _item in _items:
                        _nom = float(_item.get("nominal_adjust", 0) or 0)
                        _sign = "+" if _nom >= 0 else ""
                        _resp_text += f"- 🏪 **{_item.get('rak_id', '?')}**: {_sign}Rp {int(abs(_nom)):,}".replace(",", ".") + "\n"

                    _resp_text += f"\n💰 **Total:** {fmt_rp_signed(_total_nominal)}"

                    if _warnings:
                        _resp_text += "\n\n⚠️ " + "\n⚠️ ".join(_warnings)

                    st.markdown(_resp_text)

                    # Simpan response
                    st.session_state["yui_history"].append({"role": "assistant", "content": _resp_text})
                    save_message("yui", _session_id, "assistant", _resp_text)

                    # Set pending
                    st.session_state["yui_pending_data"] = {
                        "source": "chat",
                        "tanggal": _tanggal,
                        "rak_id": _rak_id,
                        "pic": _pic,
                        "items": _items,
                        "total_nominal": _total_nominal,
                        "warnings": _warnings,
                        "missing": _missing,
                    }
                else:
                    # Fallback ke chat biasa
                    _chat_resp = yui_chat(_user_msg, st.session_state["yui_history"])
                    _resp_text = _chat_resp.get("text", "")
                    st.markdown(_resp_text)

                    st.session_state["yui_history"].append({"role": "assistant", "content": _resp_text})
                    save_message("yui", _session_id, "assistant", _resp_text)
            else:
                # Chat biasa
                _chat_resp = yui_chat(_user_msg, st.session_state["yui_history"])
                _resp_text = _chat_resp.get("text", "")
                st.markdown(_resp_text)

                st.session_state["yui_history"].append({"role": "assistant", "content": _resp_text})
                save_message("yui", _session_id, "assistant", _resp_text)

    st.rerun()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; "
    "font-family: Quicksand, sans-serif; font-size: 10px; "
    "color: #7a9b8e; letter-spacing: 1px;'>"
    "📦 Yui — Data Entry Specialist | Input SO Toko C383 📦"
    "</div>",
    unsafe_allow_html=True,
)