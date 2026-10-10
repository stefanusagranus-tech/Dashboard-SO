"""
AI Chat Yui — Pembantu Input SO (AI-2) v11 FINAL
==================================================
- Tampilan sukses via st.dialog
- Save ke 2 tabel (so_rak_harian + so_hasil)
- Konfirmasi multi-rak per tab
"""

import streamlit as st
import time
import pandas as pd
from datetime import datetime, date
from zoneinfo import ZoneInfo

from themes.theme_loader import (
    render_theme, render_theme_animations, get_theme_by_month,
)

st.set_page_config(
    page_title="Yui — Input SO", page_icon="📦",
    layout="wide", initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)

# =========================================================
# DEBUG LOG
# =========================================================
if "yui_debug_log" not in st.session_state:
    st.session_state["yui_debug_log"] = []

def yui_log(msg):
    print(msg)
    try:
        st.session_state["yui_debug_log"].append(str(msg))
        if len(st.session_state["yui_debug_log"]) > 200:
            st.session_state["yui_debug_log"] = st.session_state["yui_debug_log"][-200:]
    except Exception:
        pass

# =========================================================
# IMPORT MODULES
# =========================================================
try:
    from modules.ai_so_input import (
        parse_natural_language, parse_file_text, yui_chat,
    )
    from modules.file_reader import read_file, detect_file_type
    from modules.chat_memory import (
        save_message, load_messages, get_or_create_session_id, clear_session,
    )
    from modules.data_loader import load_rak_master
    from modules.master_shift_handler import load_personil_master
    from modules.input_handler import save_input_harian
    _YUI_OK = True
except ImportError as e:
    _YUI_OK = False
    _import_error = str(e)

try:
    from modules.file_reader import set_log_buffer as set_file_buffer
    from modules.ai_so_input import set_log_buffer as set_ai_buffer
    set_file_buffer(st.session_state["yui_debug_log"])
    set_ai_buffer(st.session_state["yui_debug_log"])
except Exception:
    pass

def fmt_rp_signed(value):
    try:
        _v = float(value)
        _sign = "+" if _v >= 0 else "-"
        return f"{_sign}Rp {int(abs(_v)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"

def fmt_rp(value):
    try:
        return f"Rp {int(float(value)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"

# =========================================================
# CSS
# =========================================================
def inject_yui_css():
    st.markdown("""
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        .main .block-container {
            max-width: 100% !important;
            padding: 1rem 2rem !important;
        }
        .stApp, .stApp * { color: #F5E6D3 !important; }
        .stApp textarea, .stApp input, .stApp [contenteditable="true"] {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
        }
        [data-testid="stChatMessage"] {
            padding: 0.85rem 1.2rem !important;
            margin-bottom: 0.6rem !important;
            border-radius: 16px !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, rgba(127, 185, 155, 0.25), rgba(232, 177, 137, 0.15)) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
            margin-left: 20% !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.85), rgba(76, 29, 149, 0.65)) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.5) !important;
            margin-right: 20% !important;
        }
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.6) !important;
            border-radius: 16px !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
        }
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
        .rak-group-header {
            background: linear-gradient(90deg, rgba(127, 185, 155, 0.2), rgba(76, 29, 149, 0.15));
            border-left: 4px solid #7FB99B;
            border-radius: 8px;
            padding: 10px 16px;
            margin: 16px 0 8px 0;
            font-family: 'Cinzel', serif;
            font-size: 14px;
            font-weight: 900;
            color: #7FB99B;
            letter-spacing: 2px;
        }
        .rak-group-total {
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
            font-size: 12px;
            color: #E8B189;
            padding: 6px 16px;
            margin-bottom: 8px;
        }
        .metric-clean {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #7FB99B;
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 8px;
        }
        .metric-clean .label {
            font-family: 'Quicksand', sans-serif;
            font-size: 9px;
            color: #A89B8E;
            letter-spacing: 1.5px;
        }
        .metric-clean .value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 20px;
            font-weight: 900;
            color: #F5E6D3;
            margin-top: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

inject_yui_css()

if not _YUI_OK:
    st.error(f"❌ Gagal import: {_import_error}")
    st.stop()

# =========================================================
# LOAD MASTER
# =========================================================
@st.cache_data(ttl=60, show_spinner=False)
def _load_master():
    return load_rak_master(), load_personil_master(only_active=True)

_rak_df, _personil_df = _load_master()
_personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []
_rak_list = _rak_df["rak_id"].tolist() if not _rak_df.empty else []

# =========================================================
# HEADER
# =========================================================
def render_header():
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")

    _col_back, _col_title, _col_status = st.columns([1, 3, 1])

    with _col_back:
        if st.button("← Dashboard", key="btn_back_yui", width="stretch"):
            try:
                st.switch_page("Dashboard.py")
            except Exception:
                st.warning("⚠️ Gagal pindah.")

    with _col_title:
        st.markdown(
            "<div style='text-align: center;'>"
            "<div style='font-family: Cinzel, serif; font-size: 22px; font-weight: 900; "
            "color: #7FB99B; letter-spacing: 2px; text-shadow: 0 0 15px rgba(127, 185, 155, 0.6);'>"
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

render_header()

# =========================================================
# SESSION STATE
# =========================================================
_session_id = get_or_create_session_id("yui")

if "yui_history" not in st.session_state:
    with st.spinner("⏳ Load chat..."):
        _saved = load_messages("yui", _session_id, limit=100)
    st.session_state["yui_history"] = [
        {"role": _m.get("role", "user"), "content": _m.get("content", "")}
        for _m in _saved
    ]

if "yui_pending_data" not in st.session_state:
    st.session_state["yui_pending_data"] = None

if "yui_rak_to_delete" not in st.session_state:
    st.session_state["yui_rak_to_delete"] = None

if "yui_save_result" not in st.session_state:
    st.session_state["yui_save_result"] = None
    
if "yui_show_rekap" not in st.session_state:
    st.session_state["yui_show_rekap"] = False
    
if not st.session_state["yui_history"]:
    _welcome = (
        "📦 **Halo Bos!** Aku Yui, siap bantu urusan input SO.\n\n"
        "Upload file (PDF/Excel/Screenshot) atau ketik langsung:\n"
        "`Q51 minus 28rb, PIC Pandu`\n\n"
        "Gas aja Bos, aku standby 👌"
    )
    st.session_state["yui_history"].append({"role": "assistant", "content": _welcome})
    save_message("yui", _session_id, "assistant", _welcome)

_total_msg = len(st.session_state["yui_history"])
st.markdown(
    f"<div class='memory-info'>"
    f"🧠 <b>Memory Aktif</b> | Session: <code style='color: #E8B189;'>{_session_id[-15:]}</code> | "
    f"Total: <b style='color: #7FB99B;'>{_total_msg}</b> pesan"
    f"</div>",
    unsafe_allow_html=True,
)

# =========================================================
# TOOLBAR
# =========================================================
st.markdown("#### ⚡ Aksi Cepat")
_col_t1, _col_t2, _col_t3 = st.columns(3)

with _col_t1:
    if st.button("📎 Upload File", width="stretch", key="btn_yui_upload"):
        st.session_state["yui_show_upload"] = True

with _col_t2:
    if st.button("📊 Rekap SO", width="stretch", key="btn_yui_rekap"):
        st.session_state["yui_show_rekap"] = True

with _col_t3:
    if st.button("🗑️ Reset", width="stretch", key="btn_yui_reset"):
        clear_session("yui", _session_id)
        st.session_state["yui_history"] = []
        st.session_state["yui_pending_data"] = None
        st.session_state["yui_rak_to_delete"] = None
        st.session_state["yui_save_result"] = None
        st.session_state["yui_debug_log"] = []
        st.rerun()

with st.expander("🐛 Debug Log", expanded=False):
    _debug_log = st.session_state.get("yui_debug_log", [])
    if _debug_log:
        st.code("\n".join(_debug_log[-50:]), language="log")
        if st.button("🗑️ Clear Log", key="btn_clear_yui_log"):
            st.session_state["yui_debug_log"] = []
            st.rerun()
    else:
        st.caption("📭 Belum ada log.")

st.markdown("---")

# =========================================================
# DIALOG UPLOAD
# =========================================================
@st.dialog("📎 Upload File SO", width="large")
def _dialog_upload_file():
    _uploaded = st.file_uploader(
        "Pilih file",
        type=["pdf", "png", "jpg", "jpeg", "webp", "xlsx", "xls", "csv"],
        key="yui_file_upload", label_visibility="collapsed",
    )

    with st.expander("➕ Tambah Konteks (Opsional)", expanded=False):
        _col_c1, _col_c2 = st.columns(2)
        with _col_c1:
            _tgl_ctx = st.date_input(
                "Tanggal SO",
                value=datetime.now(ZoneInfo("Asia/Jakarta")).date(),
                key="yui_file_tgl",
            )
        with _col_c2:
            _rak_ctx = st.text_input("Kode Rak (kalau gak ada di file)",
                                     placeholder="Contoh: Q51", key="yui_file_rak")

    st.markdown("")
    _col_proc, _col_cancel = st.columns(2)

    with _col_proc:
        if st.button("🔍 PROSES FILE", width="stretch", type="primary",
                     key="btn_yui_process_file", disabled=(not _uploaded)):
            if not _uploaded:
                st.error("⚠️ Pilih file dulu")
                return

            st.session_state["yui_file_to_process"] = {
                "name": _uploaded.name,
                "bytes": _uploaded.getvalue(),
                "type": detect_file_type(_uploaded.name),
                "tanggal": _tgl_ctx.isoformat() if _tgl_ctx else None,
                "rak_id": _rak_ctx.strip().upper() if _rak_ctx else None,
            }
            st.session_state["yui_show_upload"] = False
            st.rerun()

    with _col_cancel:
        if st.button("❌ BATAL", width="stretch", key="btn_yui_cancel_upload"):
            st.session_state["yui_show_upload"] = False
            st.rerun()

if st.session_state.get("yui_show_upload"):
    _dialog_upload_file()

# =========================================================
# DIALOG REKAP SO
# =========================================================
@st.dialog("📊 Rekap SO", width="large")
def _dialog_rekap_so():
    try:
        from modules.yui_rekap import rekap_so, cek_rak_belum_so
    except ImportError:
        st.error("❌ Module yui_rekap gak ada")
        return

    # Filter mode
    _col_m1, _col_m2 = st.columns([2, 2])
    with _col_m1:
        _mode = st.selectbox(
            "Periode",
            ["hari_ini", "minggu_ini", "bulan_ini", "custom"],
            format_func=lambda x: {
                "hari_ini": "📅 Hari Ini",
                "minggu_ini": "📆 Minggu Ini",
                "bulan_ini": "🗓️ Bulan Ini",
                "custom": "🔧 Custom Range",
            }[x],
            key="rekap_mode",
        )
    with _col_m2:
        if _mode == "custom":
            _tgl_range = st.date_input(
                "Rentang Tanggal",
                value=(datetime.now(ZoneInfo("Asia/Jakarta")).date(),
                       datetime.now(ZoneInfo("Asia/Jakarta")).date()),
                key="rekap_range",
            )
        else:
            _tgl_range = None

    if st.button("🔍 TAMPILKAN", width="stretch", type="primary", key="btn_do_rekap"):
        _start = _end = None
        if _mode == "custom" and _tgl_range and len(_tgl_range) == 2:
            _start, _end = _tgl_range

        with st.spinner("📊 Yui rekap data..."):
            _hasil = rekap_so(mode=_mode, tgl_start=_start, tgl_end=_end)

        if not _hasil.get("success"):
            st.error(f"❌ {_hasil.get('error', 'Gagal rekap')}")
            return

        st.markdown(f"**Periode:** {_hasil['periode']}")

        # Metrics
        _m1, _m2, _m3 = st.columns(3)
        with _m1:
            st.metric("🏪 Total Rak", _hasil["total_rak"])
        with _m2:
            st.metric("📦 Total Item", _hasil["total_item"])
        with _m3:
            _nom = _hasil["total_nominal"]
            st.metric(
                "💰 Total Nominal",
                f"{'+' if _nom >= 0 else '-'}Rp {int(abs(_nom)):,}".replace(",", ".")
            )

        st.markdown("---")

        # List rak
        _list_rak = _hasil.get("list_rak", [])
        if _list_rak:
            with st.expander(f"📋 Detail {len(_list_rak)} Rak", expanded=True):
                _df_rak = pd.DataFrame(_list_rak)
                _df_rak = _df_rak.rename(columns={
                    "rak_id": "Rak",
                    "total": "Nominal",
                    "pic": "PIC",
                    "tanggal": "Tanggal",
                })
                st.dataframe(_df_rak, use_container_width=True, hide_index=True)

        # Chart per hari
        _chart = _hasil.get("chart_data", [])
        if len(_chart) > 1:
            with st.expander("📈 Trend Per Hari", expanded=True):
                _df_chart = pd.DataFrame(_chart)
                st.bar_chart(
                    _df_chart.set_index("tanggal")[["nominal"]],
                    use_container_width=True,
                )
        elif len(_chart) == 1:
            st.caption(f"📊 Cuma 1 hari data: {_chart[0]['tanggal']} — Rp {int(_chart[0]['nominal']):,}".replace(",", "."))

        # Export buttons (placeholder, kita bikin nanti)
        st.markdown("---")
        st.caption("📥 Export (coming soon: PDF, Excel, Text)")

    # Cek rak belum SO
    st.markdown("---")
    with st.expander("🔍 Cek Rak Belum SO Hari Ini", expanded=False):
        if st.button("Cek Sekarang", key="btn_cek_belum_so"):
            _belum = cek_rak_belum_so()
            if _belum:
                st.warning(f"⚠️ **{len(_belum)} rak** belum di-SO hari ini")
                st.dataframe(pd.DataFrame(_belum), use_container_width=True, hide_index=True)
            else:
                st.success("✅ Semua rak udah di-SO hari ini!")


if st.session_state.get("yui_show_rekap"):
    _dialog_rekap_so()
    
# =========================================================
# RENDER CHAT HISTORY
# =========================================================
st.markdown("#### 💬 Percakapan")
for _msg in st.session_state["yui_history"]:
    _role = _msg.get("role", "user")
    with st.chat_message(_role, avatar="👤" if _role == "user" else "📦"):
        st.markdown(_msg.get("content", ""))

# =========================================================
# PROCESS FILE
# =========================================================
if st.session_state.get("yui_file_to_process"):
    _fd = st.session_state["yui_file_to_process"]
    _file_name = _fd["name"]
    _file_bytes = _fd["bytes"]
    _tgl_ctx = _fd.get("tanggal")
    _rak_ctx = _fd.get("rak_id")

    yui_log(f"[Yui] Processing: {_file_name}")

    with st.chat_message("assistant", avatar="📦"):
        st.markdown(f"📎 Aku baca **{_file_name}** dulu ya... ⏳")

    with st.spinner(f"📦 Yui baca file..."):
        _read_result = read_file(_file_bytes, _file_name,
                                 nama_personil="", bulan=None, tahun=None)

    yui_log(f"[Yui] Read: success={_read_result.get('success')}, type={_read_result.get('type')}")

    if not _read_result.get("success"):
        _err = f"❌ Gagal baca: {_read_result.get('error')}"
        with st.chat_message("assistant", avatar="📦"):
            st.markdown(_err)
        st.session_state["yui_history"].append({"role": "assistant", "content": _err})
        save_message("yui", _session_id, "assistant", _err)
        st.session_state["yui_file_to_process"] = None
        st.rerun()

    _ocr_text = _read_result.get("text", "")
    yui_log(f"[Yui] OCR text: {len(_ocr_text)} chars")

    with st.spinner("📦 Yui olah data..."):
        _ctx = {"tanggal": _tgl_ctx, "rak_id": _rak_ctx, "pic": None}
        _parse_result = parse_file_text(
            _ocr_text,
            file_type=_read_result.get("type", "unknown"),
            context=_ctx,
            primary_df=_read_result.get("primary_df"),
        )

    yui_log(f"[Yui] Parse: success={_parse_result.get('success')}, model={_parse_result.get('model')}")

    if not _parse_result.get("success"):
        _fail = f"❌ Gagal extract: {_parse_result.get('warnings', [''])[0]}"
        with st.chat_message("assistant", avatar="📦"):
            st.markdown(_fail)
        st.session_state["yui_history"].append({"role": "assistant", "content": _fail})
        save_message("yui", _session_id, "assistant", _fail)
        st.session_state["yui_file_to_process"] = None
        st.rerun()

    _data = _parse_result.get("data", {}) or {}
    _items = _data.get("items", [])
    _items_by_rak = _data.get("items_by_rak", {})
    _total_nom = _data.get("total_nominal", 0)
    _tanggal = _data.get("tanggal") or _tgl_ctx or datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat()

    if not _items_by_rak and _items:
        yui_log("[Yui] items_by_rak kosong, fallback grouping manual")
        _grouped = {}
        for _it in _items:
            _r = _it.get("rak_id") or "UNKNOWN"
            _grouped.setdefault(_r, []).append(_it)
        _items_by_rak = _grouped

    yui_log(f"[Yui] Extracted: {len(_items)} items, {len(_items_by_rak)} rak(s)")

    with st.chat_message("assistant", avatar="📦"):
        _msg = f"✅ File **{_file_name}** berhasil aku baca!\n\n"
        _msg += f"📊 **Ringkasan:**\n"
        _msg += f"- 📅 Tanggal: **{_tanggal}**\n"
        _msg += f"- 🏪 Rak: **{len(_items_by_rak)} rak**\n"
        _msg += f"- 📦 Total item: **{len(_items)}**\n"
        _msg += f"- 💰 Total: **{fmt_rp(_total_nom)}**"
        st.markdown(_msg)

    st.session_state["yui_history"].append({"role": "assistant", "content": _msg})
    save_message("yui", _session_id, "assistant", _msg)

    st.session_state["yui_pending_data"] = {
        "source": "file",
        "file_name": _file_name,
        "tanggal": _tanggal,
        "items": _items,
        "items_by_rak": _items_by_rak,
        "total_nominal": _total_nom,
        "pics": {},
    }
    st.session_state["yui_file_to_process"] = None
    st.rerun()


# =========================================================
# DIALOG KONFIRMASI HAPUS RAK
# =========================================================
if st.session_state.get("yui_rak_to_delete"):
    _rak_del = st.session_state["yui_rak_to_delete"]

    @st.dialog(f"🗑️ Hapus Rak {_rak_del}?")
    def _dialog_confirm_delete():
        st.warning(
            f"Rak **{_rak_del}** bakal dihapus dari daftar konfirmasi.\n\n"
            f"Data ini belum tersimpan ke database — jadi aman dibatalkan."
        )

        _c_yes, _c_no = st.columns(2)

        with _c_yes:
            if st.button("✅ Ya, Hapus", width="stretch", type="primary", key="btn_confirm_del"):
                _pending_now = st.session_state.get("yui_pending_data", {})
                _by_rak = _pending_now.get("items_by_rak", {})

                if _rak_del in _by_rak:
                    del _by_rak[_rak_del]
                _pending_now["items_by_rak"] = _by_rak

                _sisa_items = []
                for _r, _items in _by_rak.items():
                    for _it in _items:
                        _sisa_items.append(_it)
                _pending_now["items"] = _sisa_items
                _pending_now["total_nominal"] = sum(
                    float(i.get("nominal_adjust", 0) or 0) for i in _sisa_items
                )

                _pics_now = _pending_now.get("pics", {})
                if _rak_del in _pics_now:
                    del _pics_now[_rak_del]
                _pending_now["pics"] = _pics_now

                st.session_state["yui_pending_data"] = _pending_now
                st.session_state["yui_rak_to_delete"] = None
                st.rerun()

        with _c_no:
            if st.button("❌ Batal", width="stretch", key="btn_cancel_del"):
                st.session_state["yui_rak_to_delete"] = None
                st.rerun()

    _dialog_confirm_delete()

# =========================================================
# HELPER: SAVE & CLOSE
# =========================================================
def _save_and_close(edited_by_rak, pics_per_rak, pending_inner):
    """Simpan semua rak ke DB, set result buat dialog sukses."""
    _saved_count = 0
    _error_count = 0
    _errors = []
    _total_nominal = 0
    _total_items = 0

    yui_log(f"[Yui] === SAVE START: {len(edited_by_rak)} rak ===")

    for _rak_id, _rak_items_final in edited_by_rak.items():
        _rak_pic = pics_per_rak.get(_rak_id, "")
        if not _rak_pic:
            yui_log(f"[Yui] Skip rak {_rak_id}: PIC kosong")
            _errors.append(f"Rak {_rak_id}: PIC kosong")
            _error_count += 1
            continue
        if not _rak_items_final:
            yui_log(f"[Yui] Skip rak {_rak_id}: item kosong")
            _errors.append(f"Rak {_rak_id}: item kosong")
            _error_count += 1
            continue

        yui_log(f"[Yui] Saving rak {_rak_id}: {len(_rak_items_final)} items, PIC={_rak_pic}")

        try:
            _ok, _msg, _detail = save_input_harian(
                tanggal=datetime.strptime(pending_inner["tanggal"], "%Y-%m-%d").date(),
                spd=0,
                rak_items=_rak_items_final,
                keterangan=f"Input via Yui ({pending_inner.get('file_name', '')})",
                pic=_rak_pic,
                update_status_rak=True,
            )
            if _ok:
                _saved_count += 1
                _total_nominal += float(_detail.get("total_nominal", 0) or 0)
                _total_items += int(_detail.get("hasil_saved", 0) or 0)
                yui_log(f"[Yui] ✅ Saved rak {_rak_id}: {len(_rak_items_final)} items")
            else:
                _error_count += 1
                _errors.append(f"Rak {_rak_id}: {_msg[:100]}")
                yui_log(f"[Yui] ❌ Save fail rak {_rak_id}: {_msg}")
        except Exception as _e:
            _error_count += 1
            _errors.append(f"Rak {_rak_id}: {str(_e)[:100]}")
            yui_log(f"[Yui] Save error {_rak_id}: {_e}")

    yui_log(f"[Yui] === SAVE DONE: {_saved_count} OK, {_error_count} error ===")

    # Simpan result untuk dialog
    st.session_state["yui_save_result"] = {
        "saved_count": _saved_count,
        "error_count": _error_count,
        "errors": _errors,
        "total": _total_nominal,
        "items": _total_items,
        "rak_saved_ids": list(edited_by_rak.keys()),
    }

    # Update history chat
    if _saved_count > 0:
        _success_msg = (
            f"🎉 **Beres Bos!** {_saved_count} rak tersimpan.\n"
            f"Total: **{fmt_rp_signed(_total_nominal)}**"
        )
        st.session_state["yui_history"].append({"role": "assistant", "content": _success_msg})
        save_message("yui", _session_id, "assistant", _success_msg)

        # Clear pending
        st.session_state["yui_pending_data"] = None
        st.cache_data.clear()
    else:
        _fail_msg = (
            f"❌ **Gagal simpan.** {_error_count} rak error.\n"
            + "\n".join([f"- {e}" for e in _errors[:5]])
        )
        st.session_state["yui_history"].append({"role": "assistant", "content": _fail_msg})
        save_message("yui", _session_id, "assistant", _fail_msg)

    st.rerun()


# =========================================================
# KONFIRMASI MULTI-RAK + MULTI-PIC (st.dialog)
# =========================================================
if st.session_state.get("yui_pending_data"):
    _pending = st.session_state["yui_pending_data"]
    _items_by_rak = _pending.get("items_by_rak", {})

    @st.dialog("📋 Konfirmasi Data SO", width="large")
    def _dialog_konfirmasi():
        _pending_inner = st.session_state["yui_pending_data"]
        _items_by_rak_inner = _pending_inner.get("items_by_rak", {})

        st.caption("Koreksi item, isi PIC per rak, atau tambah item manual")

        _c1, _c2, _c3 = st.columns(3)
        with _c1:
            st.metric("📅 Tanggal", _pending_inner.get("tanggal", "-"))
        with _c2:
            st.metric("🏪 Total Rak", len(_items_by_rak_inner))
        with _c3:
            st.metric("📦 Total Item", len(_pending_inner.get("items", [])))

        st.markdown("---")

        _edited_by_rak = {}
        _pics_per_rak = _pending_inner.get("pics", {})

        _rak_ids = list(_items_by_rak_inner.keys())
        if _rak_ids:
            _tabs = st.tabs([f"🏪 {_r}" for _r in _rak_ids])

            for _tab, _rak_id in zip(_tabs, _rak_ids):
                with _tab:
                    _rak_items = _items_by_rak_inner[_rak_id]

                    _c_pic, _c_del = st.columns([3, 1])
                    with _c_pic:
                        if _personil_list:
                            _current_pic = _pics_per_rak.get(_rak_id, "")
                            _pic_options = [""] + _personil_list
                            _pic_idx = _pic_options.index(_current_pic) if _current_pic in _pic_options else 0
                            _new_pic = st.selectbox(
                                f"👤 PIC untuk {_rak_id}",
                                options=_pic_options,
                                index=_pic_idx,
                                key=f"pic_rak_{_rak_id}",
                            )
                            if _new_pic:
                                _pics_per_rak[_rak_id] = _new_pic
                        else:
                            _new_pic = st.text_input(
                                f"👤 PIC untuk {_rak_id}",
                                placeholder="Nama PIC",
                                key=f"pic_rak_{_rak_id}",
                            )
                            if _new_pic:
                                _pics_per_rak[_rak_id] = _new_pic

                    with _c_del:
                        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                        if st.button("🗑️ Hapus", key=f"btn_del_rak_{_rak_id}", width="stretch"):
                            st.session_state["yui_rak_to_delete"] = _rak_id
                            st.rerun()

                    _df_rak = pd.DataFrame(_rak_items)
                    _rename_map = {
                        "plu": "PLU",
                        "nama_produk": "Nama Produk",
                        "qty_sistem": "Qty Sistem",
                        "qty_fisik": "Qty Fisik",
                        "qty_var": "Qty Var",
                        "nominal_adjust": "Nominal",
                    }
                    _cols_show_src = ["plu", "nama_produk", "qty_sistem", "qty_fisik", "nominal_adjust"]
                    _cols_show_src = [c for c in _cols_show_src if c in _df_rak.columns]
                    _df_rak = _df_rak[_cols_show_src].rename(columns=_rename_map)

                    if "Qty Sistem" in _df_rak.columns and "Qty Fisik" in _df_rak.columns:
                        _df_rak["Qty Var"] = (
                            pd.to_numeric(_df_rak["Qty Fisik"], errors="coerce").fillna(0).astype(int)
                            - pd.to_numeric(_df_rak["Qty Sistem"], errors="coerce").fillna(0).astype(int)
                        )

                    _col_order = ["PLU", "Nama Produk", "Qty Sistem", "Qty Fisik", "Qty Var", "Nominal"]
                    _col_order = [c for c in _col_order if c in _df_rak.columns]
                    _df_rak = _df_rak[_col_order]

                    _edited_rak = st.data_editor(
                        _df_rak,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",
                        height=min(400, 80 + len(_df_rak) * 38),
                        column_config={
                            "PLU": st.column_config.TextColumn("PLU", width="small"),
                            "Nama Produk": st.column_config.TextColumn("Nama Produk", width="large"),
                            "Qty Sistem": st.column_config.NumberColumn("Qty Sistem", width="small"),
                            "Qty Fisik": st.column_config.NumberColumn("Qty Fisik", width="small"),
                            "Qty Var": st.column_config.NumberColumn(
                                "Qty Var", width="small", disabled=True,
                                help="Auto: Qty Fisik − Qty Sistem"
                            ),
                            "Nominal": st.column_config.NumberColumn("Nominal", format="Rp %d", width="medium"),
                        },
                        key=f"editor_rak_{_rak_id}",
                    )

                    _items_this_rak = []
                    for _, _r in _edited_rak.iterrows():
                        _plu = str(_r.get("PLU", "") or "").strip()
                        _nama = str(_r.get("Nama Produk", "") or "").strip()
                        if not _plu and not _nama:
                            continue
                        _qty_sist = int(_r.get("Qty Sistem", 0) or 0)
                        _qty_fis = int(_r.get("Qty Fisik", 0) or 0)
                        _items_this_rak.append({
                            "rak_id": _rak_id,
                            "plu": _plu,
                            "nama_produk": _nama,
                            "qty_sistem": _qty_sist,
                            "qty_fisik": _qty_fis,
                            "qty_var": _qty_fis - _qty_sist,
                            "nominal_adjust": float(_r.get("Nominal", 0) or 0),
                            "pic": _pics_per_rak.get(_rak_id),
                        })

                    _edited_by_rak[_rak_id] = _items_this_rak

                    _rak_total = sum(float(i["nominal_adjust"]) for i in _items_this_rak)
                    _total_color = "#E88B8B" if _rak_total < 0 else "#7FB99B"
                    st.markdown(
                        f"<div class='rak-group-total'>💰 Total {_rak_id}: "
                        f"<b style='color: {_total_color};'>{fmt_rp_signed(_rak_total)}</b></div>",
                        unsafe_allow_html=True,
                    )

        _updated_items_all = []
        for _r, _items_list in _edited_by_rak.items():
            _updated_items_all.extend(_items_list)

        _pending_inner["items"] = _updated_items_all
        _pending_inner["items_by_rak"] = _edited_by_rak
        _pending_inner["pics"] = _pics_per_rak
        _new_total = sum(i["nominal_adjust"] for i in _updated_items_all)
        _pending_inner["total_nominal"] = _new_total
        st.session_state["yui_pending_data"] = _pending_inner

        _rak_tanpa_pic = [r for r in _edited_by_rak.keys() if not _pics_per_rak.get(r)]
        if _rak_tanpa_pic:
            st.warning(f"⚠️ Rak belum ada PIC: **{', '.join(_rak_tanpa_pic)}**")

        _total_color = "#E88B8B" if _new_total < 0 else "#7FB99B"
        st.markdown(
            f"<div class='metric-clean' style='border-left-color: {_total_color}; text-align: right; margin-top: 16px;'>"
            f"<div class='label'>💰 TOTAL SEMUA</div>"
            f"<div class='value' style='color: {_total_color};'>{fmt_rp_signed(_new_total)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        _c_save, _c_cancel = st.columns(2)

        with _c_save:
            if st.button("💾 SIMPAN SEMUA", width="stretch", type="primary",
                         key="btn_yui_save_so",
                         disabled=(bool(_rak_tanpa_pic) or not _edited_by_rak)):
                _save_and_close(_edited_by_rak, _pics_per_rak, _pending_inner)

        with _c_cancel:
            if st.button("❌ BATAL", width="stretch", key="btn_yui_cancel_pending"):
                _cancel = "Oke Bos, aku batalkan."
                st.session_state["yui_history"].append({"role": "assistant", "content": _cancel})
                save_message("yui", _session_id, "assistant", _cancel)
                st.session_state["yui_pending_data"] = None
                st.rerun()

    _dialog_konfirmasi()


# =========================================================
# DIALOG SUKSES / GAGAL
# =========================================================
if st.session_state.get("yui_save_result"):
    _sr = st.session_state["yui_save_result"]

    @st.dialog("🎉 Hasil Simpan")
    def _dialog_save_result():
        _saved = _sr.get("saved_count", 0)
        _errors = _sr.get("error_count", 0)
        _total = _sr.get("total", 0)
        _items = _sr.get("items", 0)
        _err_list = _sr.get("errors", [])
        _rak_ids = _sr.get("rak_saved_ids", [])

        if _saved > 0 and _errors == 0:
            st.success(f"✅ **{_saved} rak** berhasil tersimpan!")
            st.markdown(
                f"<div style='text-align: center; padding: 16px; "
                f"background: rgba(20, 12, 35, 0.95); border-radius: 12px; margin: 12px 0;'>"
                f"<div style='font-family: Quicksand; font-size: 10px; color: #A89B8E; "
                f"letter-spacing: 1.5px;'>TOTAL NOMINAL</div>"
                f"<div style='font-family: JetBrains Mono; font-size: 28px; font-weight: 900; "
                f"color: {'#E88B8B' if _total < 0 else '#7FB99B'}; margin-top: 8px;'>"
                f"{fmt_rp_signed(_total)}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            _rak_str = ", ".join(_rak_ids) if _rak_ids else "-"
            st.caption(f"🏪 Rak tersimpan: **{_rak_str}**")

        elif _saved > 0 and _errors > 0:
            st.warning(f"⚠️ **{_saved} rak tersimpan**, {_errors} rak gagal.")
            st.markdown(
                f"<div style='text-align: center; padding: 16px; "
                f"background: rgba(20, 12, 35, 0.95); border-radius: 12px; margin: 12px 0;'>"
                f"<div style='font-family: Quicksand; font-size: 10px; color: #A89B8E;'>"
                f"TOTAL TERSIMPAN</div>"
                f"<div style='font-family: JetBrains Mono; font-size: 24px; font-weight: 900; "
                f"color: #E8B189; margin-top: 8px;'>{fmt_rp_signed(_total)}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            with st.expander("❌ Detail Error", expanded=True):
                for _e in _err_list[:10]:
                    st.caption(f"- {_e}")

        else:
            st.error(f"❌ **Gagal simpan.** {_errors} rak error.")
            with st.expander("❌ Detail Error", expanded=True):
                for _e in _err_list[:10]:
                    st.caption(f"- {_e}")

        st.markdown("")
        if st.button("✅ Tutup", width="stretch", type="primary", key="btn_close_save_result"):
            st.session_state["yui_save_result"] = None
            st.rerun()

    _dialog_save_result()


# =========================================================
# CHAT INPUT
# =========================================================
_preset = st.session_state.pop("yui_preset", "")
_user_msg = st.chat_input("Ketik atau upload file buat Yui...", key="yui_chat_input")

if _preset and not _user_msg:
    _user_msg = _preset

if _user_msg:
    st.session_state["yui_history"].append({"role": "user", "content": _user_msg})
    save_message("yui", _session_id, "user", _user_msg)

    with st.chat_message("user", avatar="👤"):
        st.markdown(_user_msg)

    _user_lower = _user_msg.lower()
    _is_so_input = any(kw in _user_lower for kw in [
        "rak", "q51", "minus", "plus", "so ", "input so", "selisih",
        "pic ", "rp ", "ribu", "rb",
    ])

    with st.chat_message("assistant", avatar="📦"):
        with st.spinner("📦 Aku cek..."):
            if _is_so_input:
                _parse = parse_natural_language(_user_msg, _rak_list[:100])
                if _parse.get("success") and _parse.get("data"):
                    _data = _parse["data"]
                    _items = _data.get("items", [])
                    _tanggal = _data.get("tanggal", datetime.now(ZoneInfo("Asia/Jakarta")).date().isoformat())
                    _total = sum(float(i.get("nominal_adjust", 0) or 0) for i in _items)

                    _resp = f"📦 Oke Bos, aku catat:\n\n- 📅 {_tanggal}\n"
                    for _item in _items:
                        _nom = float(_item.get("nominal_adjust", 0) or 0)
                        _resp += f"- 🏪 **{_item.get('rak_id', '?')}**: {fmt_rp_signed(_nom)}\n"
                    _resp += f"\n💰 Total: **{fmt_rp_signed(_total)}**"

                    st.markdown(_resp)
                    st.session_state["yui_history"].append({"role": "assistant", "content": _resp})
                    save_message("yui", _session_id, "assistant", _resp)

                    _grouped = {}
                    for _item in _items:
                        _rak = _item.get("rak_id", "UNKNOWN")
                        _grouped.setdefault(_rak, []).append(_item)

                    st.session_state["yui_pending_data"] = {
                        "source": "chat",
                        "tanggal": _tanggal,
                        "items": _items,
                        "items_by_rak": _grouped,
                        "total_nominal": _total,
                        "pics": {},
                    }
                else:
                    _chat = yui_chat(_user_msg, st.session_state["yui_history"])
                    _resp = _chat.get("text", "")
                    st.markdown(_resp)
                    st.session_state["yui_history"].append({"role": "assistant", "content": _resp})
                    save_message("yui", _session_id, "assistant", _resp)
            else:
                _chat = yui_chat(_user_msg, st.session_state["yui_history"])
                _resp = _chat.get("text", "")
                st.markdown(_resp)
                st.session_state["yui_history"].append({"role": "assistant", "content": _resp})
                save_message("yui", _session_id, "assistant", _resp)

    st.rerun()


# =========================================================
# FOOTER
# =========================================================
st.markdown(
    "<div style='text-align: center; padding: 20px 0; font-family: Quicksand; "
    "font-size: 10px; color: #7a9b8e; letter-spacing: 1px;'>"
    "📦 Yui — Data Entry Specialist | Input SO Toko C383 📦"
    "</div>",
    unsafe_allow_html=True,
)