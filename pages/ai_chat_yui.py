"""
AI Chat Yui — Pembantu Input SO (AI-2) v7
==========================================
Konfirmasi multi-rak + multi-PIC + edit manual.
"""

import streamlit as st
import time
from datetime import datetime
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

if "yui_last_saved" not in st.session_state:
    st.session_state["yui_last_saved"] = None


# Welcome
if not st.session_state["yui_history"]:
    _welcome = (
        "📦 **Halo Bos!** Aku Yui, siap bantu urusan input SO.\n\n"
        "Upload file (PDF/Excel/Screenshot) atau ketik langsung:\n"
        "`Q51 minus 28rb, PIC Pandu`\n\n"
        "Gas aja Bos, aku standby 👌"
    )
    st.session_state["yui_history"].append({"role": "assistant", "content": _welcome})
    save_message("yui", _session_id, "assistant", _welcome)


if st.session_state["yui_last_saved"]:
    st.success(st.session_state["yui_last_saved"])
    st.session_state["yui_last_saved"] = None


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
        st.session_state["yui_preset"] = "Rekap SO aku dong hari ini"

with _col_t3:
    if st.button("🗑️ Reset", width="stretch", key="btn_yui_reset"):
        clear_session("yui", _session_id)
        st.session_state["yui_history"] = []
        st.session_state["yui_pending_data"] = None
        st.session_state["yui_debug_log"] = []
        st.rerun()


# Debug log
with st.expander("🐛 Debug Log (klik untuk buka)", expanded=False):
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
    st.markdown(
        "<div style='font-family: Quicksand; font-size: 12px; color: #A89B8E; "
        "margin-bottom: 12px;'>Upload file laporan SO (PDF, foto, Excel, CSV).</div>",
        unsafe_allow_html=True,
    )

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

    yui_log(f"[Yui] Extracted: {len(_items)} items, {len(_items_by_rak)} rak(s)")

    # ✅ Konfirmasi di chat
    with st.chat_message("assistant", avatar="📦"):
        _msg = f"✅ File **{_file_name}** berhasil aku baca!\n\n"
        _msg += f"📊 **Ringkasan:**\n"
        _msg += f"- 📅 Tanggal: **{_tanggal}**\n"
        _msg += f"- 🏪 Rak: **{len(_items_by_rak)} rak**\n"
        _msg += f"- 📦 Total item: **{len(_items)}**\n"
        _msg += f"- 💰 Total: **Rp {int(_total_nom):,}**".replace(",", ".")
        st.markdown(_msg)

    st.session_state["yui_history"].append({"role": "assistant", "content": _msg})
    save_message("yui", _session_id, "assistant", _msg)

    # Simpan pending — TANPA "missing"
    st.session_state["yui_pending_data"] = {
        "source": "file",
        "file_name": _file_name,
        "tanggal": _tanggal,
        "items": _items,
        "items_by_rak": _items_by_rak,
        "total_nominal": _total_nom,
        "pics": {},  # {rak_id: pic}
    }
    st.session_state["yui_file_to_process"] = None
    st.rerun()


# =========================================================
# KONFIRMASI MULTI-RAK + MULTI-PIC
# =========================================================
if st.session_state.get("yui_pending_data"):
    _pending = st.session_state["yui_pending_data"]
    _items_by_rak = _pending.get("items_by_rak", {})

    st.markdown("---")
    st.markdown("#### 📋 Konfirmasi Data SO")
    st.caption("Koreksi item, isi PIC per rak, atau tambah item manual")

    # Info summary
    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>📅 TANGGAL</div>"
            f"<div class='value' style='font-size: 16px;'>{_pending.get('tanggal', '-')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _c2:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>🏪 TOTAL RAK</div>"
            f"<div class='value' style='font-size: 16px;'>{len(_items_by_rak)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with _c3:
        st.markdown(
            f"<div class='metric-clean'>"
            f"<div class='label'>📦 TOTAL ITEM</div>"
            f"<div class='value' style='font-size: 16px;'>{len(_pending.get('items', []))}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("")

    # Per rak — tabel editable + PIC
    _updated_items_all = []
    _pics_per_rak = _pending.get("pics", {})

    for _rak_id, _rak_items in _items_by_rak.items():
        _col_h1, _col_h2 = st.columns([2, 2])

        with _col_h1:
            st.markdown(
                f"<div class='rak-group-header'>🏪 RAK: {_rak_id}</div>",
                unsafe_allow_html=True,
            )

        with _col_h2:
            if _personil_list:
                _current_pic = _pics_per_rak.get(_rak_id, "")
                _pic_idx = _personil_list.index(_current_pic) if _current_pic in _personil_list else 0
                _new_pic = st.selectbox(
                    f"👤 PIC untuk {_rak_id}",
                    options=[""] + _personil_list,
                    index=(_pic_idx + 1) if _current_pic else 0,
                    key=f"pic_rak_{_rak_id}",
                    label_visibility="collapsed",
                )
                if _new_pic:
                    _pics_per_rak[_rak_id] = _new_pic
            else:
                _new_pic = st.text_input(
                    f"👤 PIC untuk {_rak_id}",
                    placeholder="Nama PIC",
                    key=f"pic_rak_{_rak_id}",
                    label_visibility="collapsed",
                )
                if _new_pic:
                    _pics_per_rak[_rak_id] = _new_pic

        # Tabel editable — pakai num_rows="dynamic"
        _df_rak = pd.DataFrame(_rak_items)
        _cols_show = ["plu", "nama_produk", "qty_sistem", "qty_fisik", "qty_var", "nominal_adjust"]
        _cols_show = [c for c in _cols_show if c in _df_rak.columns]
        _df_rak = _df_rak[_cols_show]

        _df_rak = _df_rak.rename(columns={
            "plu": "PLU",
            "nama_produk": "Nama Produk",
            "qty_sistem": "Qty Sistem",
            "qty_fisik": "Qty Fisik",
            "qty_var": "Qty Var",
            "nominal_adjust": "Nominal",
        })

        _edited_rak = st.data_editor(
            _df_rak,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",  # ✅ Bisa tambah item manual
            height=min(300, 60 + len(_df_rak) * 40),
            column_config={
                "PLU": st.column_config.TextColumn("PLU", width="small"),
                "Nama Produk": st.column_config.TextColumn("Nama Produk", width="large"),
                "Qty Sistem": st.column_config.NumberColumn("Qty Sistem", width="small"),
                "Qty Fisik": st.column_config.NumberColumn("Qty Fisik", width="small"),
                "Qty Var": st.column_config.NumberColumn("Qty Var", width="small"),
                "Nominal": st.column_config.NumberColumn("Nominal", format="Rp %d", width="medium"),
            },
            key=f"editor_rak_{_rak_id}",
        )

        _rak_total = sum(float(_r.get("Nominal", 0) or 0) for _, _r in _edited_rak.iterrows())
        st.markdown(
            f"<div class='rak-group-total'>💰 Total {_rak_id}: "
            f"<b style='color: {'#E88B8B' if _rak_total < 0 else '#7FB99B'};'>"
            f"Rp {int(_rak_total):,}</b></div>".replace(",", "."),
            unsafe_allow_html=True,
        )

        for _, _r in _edited_rak.iterrows():
            _updated_items_all.append({
                "rak_id": _rak_id,
                "plu": str(_r.get("PLU", "")),
                "nama_produk": str(_r.get("Nama Produk", "")),
                "qty_sistem": int(_r.get("Qty Sistem", 0) or 0),
                "qty_fisik": int(_r.get("Qty Fisik", 0) or 0),
                "qty_var": int(_r.get("Qty Var", 0) or 0),
                "nominal_adjust": float(_r.get("Nominal", 0) or 0),
                "pic": _pics_per_rak.get(_rak_id),
            })

    # Update pending
    st.session_state["yui_pending_data"]["items"] = _updated_items_all
    st.session_state["yui_pending_data"]["pics"] = _pics_per_rak
    _new_total = sum(i["nominal_adjust"] for i in _updated_items_all)
    st.session_state["yui_pending_data"]["total_nominal"] = _new_total

    st.markdown(
        f"<div class='metric-clean' style='border-left-color: {'#E88B8B' if _new_total < 0 else '#7FB99B'}; "
        f"text-align: right; margin-top: 16px;'>"
        f"<div class='label'>💰 TOTAL SEMUA</div>"
        f"<div class='value' style='color: {'#E88B8B' if _new_total < 0 else '#7FB99B'};'>"
        f"{fmt_rp_signed(_new_total)}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Validasi PIC
    _rak_tanpa_pic = [r for r in _items_by_rak.keys() if not _pics_per_rak.get(r)]

    if _rak_tanpa_pic:
        st.warning(f"⚠️ Rak belum ada PIC: **{', '.join(_rak_tanpa_pic)}**")

    st.markdown("")
    _col_save, _col_cancel = st.columns([2, 1])

    with _col_save:
        if st.button("💾 SIMPAN SEMUA", width="stretch", type="primary",
                     key="btn_yui_save_so", disabled=bool(_rak_tanpa_pic)):
            with st.spinner("📦 Menyimpan..."):
                _saved_count = 0
                _error_count = 0

                for _rak_id, _rak_items in _items_by_rak.items():
                    _rak_pic = _pics_per_rak.get(_rak_id, "")
                    if not _rak_pic:
                        continue

                    try:
                        _ok, _msg, _detail = save_input_harian(
                            tanggal=datetime.strptime(_pending["tanggal"], "%Y-%m-%d").date(),
                            spd=0,
                            rak_items=_rak_items,
                            keterangan=f"Input via Yui ({_pending.get('file_name', '')})",
                            pic=_rak_pic,
                            update_status_rak=True,
                        )
                        if _ok:
                            _saved_count += 1
                        else:
                            _error_count += 1
                    except Exception as _e:
                        yui_log(f"[Yui] Save error {_rak_id}: {_e}")
                        _error_count += 1

                if _saved_count > 0:
                    _success = (
                        f"🎉 **Beres Bos!** {_saved_count} rak tersimpan.\n"
                        f"Total: **{fmt_rp_signed(_new_total)}**"
                    )
                    st.session_state["yui_last_saved"] = _success
                    st.session_state["yui_history"].append({"role": "assistant", "content": _success})
                    save_message("yui", _session_id, "assistant", _success)
                    st.session_state["yui_pending_data"] = None
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ Gagal simpan. Error: {_error_count}")

    with _col_cancel:
        if st.button("❌ BATAL", width="stretch", key="btn_yui_cancel_pending"):
            _cancel = "Oke Bos, aku batalkan."
            st.session_state["yui_history"].append({"role": "assistant", "content": _cancel})
            save_message("yui", _session_id, "assistant", _cancel)
            st.session_state["yui_pending_data"] = None
            st.rerun()

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

                    # Group by rak
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