"""
AI Chat Yui — Data Entry & Audit Specialist (AI-2) v14 FINAL
==============================================================
UI: WhatsApp-style, full screen, header custom component
Semua dialog cuma trigger. Hasil rekap/export di halaman utama.

Changelog v14:
- Header 1 baris (custom component v2)
- Popover menu ⋮ (toolbar pindah ke sini)
- Chat bubble + timestamp scrollable
- Footer tipis (memory info + footer lama digabung)
- Full screen
- Logic chat, dialog & export TETAP SAMA
"""

import streamlit as st
import time
import re
import io
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import urllib.parse
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
    from modules.spd_calculator import save_spd_harian
    _YUI_OK = True
except ImportError as e:
    _YUI_OK = False
    _import_error = str(e)

try:
    from modules.yui_rekap import rekap_so, cek_rak_belum_so
    _REKAP_OK = True
except ImportError:
    _REKAP_OK = False

try:
    from modules.yui_export import export_rekap_pdf, export_rekap_image
    _EXPORT_OK = True
except ImportError:
    _EXPORT_OK = False

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

def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))

def _build_wa_link(text, phone="6285892620149"):
    _wa_text = (
        f"{text}\n\n"
        f"---\n"
        f"📦 *Pesan ini dikirim oleh Yui — Asisten SO bagian Pencatatan*"
    )
    _encoded = urllib.parse.quote(_wa_text, safe="")
    return f"https://wa.me/{phone}?text={_encoded}"

# =========================================================
# CSS — FULL SCREEN + BUBBLE + POPOVER
# =========================================================
def inject_yui_css():
    st.markdown("""
    <style>
        /* === HIDE STREAMLIT CHROME === */
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        #MainMenu { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        [data-testid="stDecoration"] { display: none !important; }

        /* === ZERO PADDING + PADDING TOP BUAT HEADER FIXED === */
        .main .block-container {
            max-width: 100% !important;
            padding: 70px 0.6rem 0.4rem 0.6rem !important;
            margin: 0 !important;
        }
        .main, .stApp, section.main { padding: 0 !important; }

        /* === COLORS === */
        .stApp, .stApp * { color: #F5E6D3 !important; }
        .stApp textarea, .stApp input, .stApp [contenteditable="true"] {
            color: #F5E6D3 !important;
            background: rgba(30, 20, 60, 0.6) !important;
        }

        /* === CHAT MESSAGES — BUBBLE === */
        [data-testid="stChatMessage"] {
            padding: 0.6rem 1rem !important;
            margin-bottom: 0.8rem !important;
            border-radius: 18px !important;
            max-width: 85% !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background: linear-gradient(135deg, rgba(127, 185, 155, 0.85), rgba(232, 177, 137, 0.6)) !important;
            border: 1px solid rgba(127, 185, 155, 0.8) !important;
            margin-left: auto !important;
            margin-right: 0 !important;
            border-bottom-right-radius: 4px !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
            background: linear-gradient(135deg, rgba(30, 20, 60, 0.95), rgba(76, 29, 149, 0.85)) !important;
            border: 1px solid rgba(127, 185, 155, 0.5) !important;
            margin-right: auto !important;
            margin-left: 0 !important;
            border-bottom-left-radius: 4px !important;
        }

        /* === CHAT INPUT === */
        [data-testid="stChatInputContainer"] {
            background: rgba(30, 20, 60, 0.9) !important;
            border-radius: 14px !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
        }

        /* === SCROLLABLE CONTAINER === */
        div[data-testid="stVerticalBlock"] > div[style*="height"] {
            background: rgba(20, 12, 35, 0.4) !important;
            border-radius: 12px !important;
            border: 1px solid rgba(127, 185, 155, 0.2) !important;
            padding: 8px !important;
        }

        /* === MEMORY INFO (footer tipis) === */
        .memory-info-footer {
            background: rgba(20, 12, 35, 0.95);
            border-left: 3px solid #7FB99B;
            border-radius: 8px;
            padding: 6px 12px;
            margin-top: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            color: #A89B8E;
            text-align: center;
        }

        /* === MODEL BADGE === */
        .model-badge {
            display: inline-block;
            background: rgba(127, 185, 155, 0.15);
            border: 1px solid rgba(127, 185, 155, 0.5);
            border-radius: 6px;
            padding: 2px 8px;
            font-family: JetBrains Mono, monospace;
            font-size: 9px;
            color: #7FB99B;
            margin-left: 8px;
        }

        /* === POPOVER === */
        [data-testid="stPopover"] > button {
            background: rgba(30, 20, 60, 0.6) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.5) !important;
            border-radius: 10px !important;
            color: #7FB99B !important;
            font-size: 18px !important;
            font-weight: 900 !important;
            height: 34px !important;
            width: 34px !important;
            padding: 0 !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stPopover"] > button:hover {
            background: rgba(127, 185, 155, 0.2) !important;
            border-color: #7FB99B !important;
        }
        [data-testid="stPopoverBody"] {
            background: rgba(20, 12, 35, 0.98) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.5) !important;
            border-radius: 12px !important;
            padding: 12px !important;
        }
        [data-testid="stPopoverBody"] button {
            background: rgba(30, 20, 60, 0.6) !important;
            border: 1px solid rgba(127, 185, 155, 0.3) !important;
            border-radius: 8px !important;
            color: #F5E6D3 !important;
            font-size: 12px !important;
            margin-bottom: 4px !important;
        }

        /* === TIMESTAMP BUBBLE === */
        .bubble-time {
            font-family: JetBrains Mono, monospace;
            font-size: 8px;
            color: rgba(245, 230, 211, 0.5);
            margin-top: 2px;
        }

        /* === DIALOG / MODAL === */
        [data-testid="stDialog"] {
            background: rgba(20, 12, 35, 0.98) !important;
            border: 1.5px solid rgba(127, 185, 155, 0.6) !important;
            border-radius: 16px !important;
        }
        [data-testid="stDialog"] h2 {
            font-family: Cinzel, serif !important;
            color: #7FB99B !important;
            font-size: 18px !important;
        }

        /* === RAK GROUP & METRIC (dialog konfirmasi) === */
        .rak-group-total {
            text-align: right; font-family: 'JetBrains Mono', monospace;
            font-size: 12px; color: #E8B189; padding: 6px 16px; margin-bottom: 8px;
        }
        .metric-clean {
            background: rgba(20, 12, 35, 0.95); border-left: 3px solid #7FB99B;
            border-radius: 8px; padding: 10px 16px; margin-bottom: 8px;
        }
        .metric-clean .label {
            font-family: 'Quicksand', sans-serif; font-size: 9px;
            color: #A89B8E; letter-spacing: 1.5px;
        }
        .metric-clean .value {
            font-family: 'JetBrains Mono', monospace; font-size: 20px;
            font-weight: 900; color: #F5E6D3; margin-top: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

inject_yui_css()

if not _YUI_OK:
    st.error(f"❌ Gagal import: {_import_error}")
    st.stop()
    
# =========================================================
# SESSION STATE
# =========================================================
_session_id = get_or_create_session_id("yui")

if "yui_history" not in st.session_state:
    with st.spinner("⏳ Load chat..."):
        _saved = load_messages("yui", _session_id, limit=100)
    st.session_state["yui_history"] = [
        {"role": _m.get("role", "user"), "content": _m.get("content", "")} for _m in _saved
    ]

_DEFAULT_STATES = {
    "yui_pending_data": None,
    "yui_rak_to_delete": None,
    "yui_save_result": None,
    "yui_show_rekap": False,
    "yui_show_spd": False,
    "yui_show_upload": False,
    "yui_show_menu": False,
    "yui_rekap_hasil": None,
    "yui_export_result": None,
    "yui_pending_spd": None,
    "yui_file_to_process": None,
}
for _k, _v in _DEFAULT_STATES.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Auto-clear pending kosong
if st.session_state.get("yui_pending_data"):
    _p_check = st.session_state["yui_pending_data"]
    _by_rak_check = _p_check.get("items_by_rak", {})
    _all_empty = all(not v for v in _by_rak_check.values()) if _by_rak_check else True
    if _all_empty:
        st.session_state["yui_pending_data"] = None

if not st.session_state["yui_history"]:
    _welcome = (
        "📦 **Halo Bos!** Aku Yui, siap bantu input, edit, hapus, dan rekap data SO.\n\n"
        "Contoh:\n"
        "- `Q51 minus 28rb, PIC Pandu`\n"
        "- `input spd hari ini 12.750.800`\n"
        "- `rekap SO minggu ini`\n\n"
        "Kalau mau analisis, tanya Rei ya 😏"
    )
    st.session_state["yui_history"].append({
        "role": "assistant", "content": _welcome,
        "time": _now_jkt().strftime("%H:%M"),
    })
    save_message("yui", _session_id, "assistant", _welcome)


# =========================================================
# HEADER 1 BARIS — CUSTOM COMPONENT V2
# =========================================================
_rei_header_component = st.components.v2.component(
    name="yui_header",
    html="""
    <div class="yui-header">
        <button id="btn-back" class="hdr-btn">←</button>
        <span class="hdr-title">📦 YUI</span>
        <button id="btn-menu" class="hdr-btn">⋮</button>
    </div>
    """,
    css="""
    .yui-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 9999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        background: linear-gradient(135deg, rgba(30, 20, 60, 0.98), rgba(76, 29, 149, 0.9));
        border-bottom: 2px solid rgba(127, 185, 155, 0.6);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        min-height: 52px;
        box-sizing: border-box;
        font-family: 'Cinzel', serif;
    }
    .hdr-btn {
        width: 40px;
        height: 36px;
        background: rgba(30, 20, 60, 0.85);
        border: 1.5px solid rgba(127, 185, 155, 0.6);
        border-radius: 10px;
        color: #7FB99B;
        font-size: 16px;
        font-weight: 900;
        cursor: pointer;
        padding: 0;
        transition: all 0.2s ease;
        flex-shrink: 0;
    }
    .hdr-btn:hover {
        background: rgba(127, 185, 155, 0.25);
        border-color: #7FB99B;
    }
    .hdr-title {
        font-size: 18px;
        font-weight: 900;
        color: #7FB99B;
        letter-spacing: 1.5px;
        text-shadow: 0 0 10px rgba(127, 185, 155, 0.6);
        text-align: center;
        flex-grow: 1;
    }
    """,
    js="""
    export default function(component) {
        const { parentElement, setTriggerValue } = component;
        const backBtn = parentElement.querySelector('#btn-back');
        const menuBtn = parentElement.querySelector('#btn-menu');
        if (backBtn) {
            backBtn.onclick = () => { setTriggerValue('back', true); };
        }
        if (menuBtn) {
            menuBtn.onclick = () => { setTriggerValue('menu', true); };
        }
    }
    """,
    isolate_styles=True,
)

_header_result = _rei_header_component(
    data={},
    key="yui_header",
    on_back_change=lambda: None,
    on_menu_change=lambda: None,
)

if _header_result.get("back"):
    try:
        st.switch_page("Dashboard.py")
    except Exception:
        st.warning("⚠️ Gagal pindah.")

if _header_result.get("menu"):
    st.session_state["yui_show_menu"] = True
    st.rerun()


# =========================================================
# MENU DIALOG (MODAL)
# =========================================================
@st.dialog("⚙️ Menu Yui", width="small")
def _yui_menu_dialog():
    st.caption("📥 INPUT")
    if st.button("📎 Upload File", use_container_width=True, key="menu_upload"):
        st.session_state["yui_show_menu"] = False
        st.session_state["yui_show_upload"] = True
        st.rerun()
    if st.button("💰 Input SPD", use_container_width=True, key="menu_spd"):
        st.session_state["yui_show_menu"] = False
        st.session_state["yui_show_spd"] = True
        st.rerun()
    if st.button("📊 Rekap SO", use_container_width=True, key="menu_rekap"):
        st.session_state["yui_show_menu"] = False
        st.session_state["yui_show_rekap"] = True
        st.rerun()

    st.divider()

    st.caption("💾 SESSION")
    if st.button("🗑️ Reset Chat", use_container_width=True, key="menu_reset"):
        clear_session("yui", _session_id)
        st.session_state["yui_history"] = []
        for _k in _DEFAULT_STATES:
            st.session_state[_k] = _DEFAULT_STATES[_k]
        st.session_state["yui_debug_log"] = []
        st.session_state["yui_show_menu"] = False
        st.rerun()

    st.divider()

    st.caption("🐛 SISTEM")
    _total_msg_menu = len(st.session_state.get("yui_history", []))
    st.caption(f"🧠 Session: `{_session_id[-12:]}`")
    st.caption(f"💬 Total: {_total_msg_menu} pesan")

    with st.expander("🐛 Debug Log", expanded=False):
        _debug_log_menu = st.session_state.get("yui_debug_log", [])
        if _debug_log_menu:
            st.code("\n".join(_debug_log_menu[-20:]), language="log")
            if st.button("🗑️ Clear Log", key="menu_clear_log"):
                st.session_state["yui_debug_log"] = []
                st.rerun()
        else:
            st.caption("📭 Belum ada log.")

    st.divider()

    if st.button("❌ Tutup", use_container_width=True, key="menu_close"):
        st.session_state["yui_show_menu"] = False
        st.rerun()


if st.session_state.get("yui_show_menu"):
    _yui_menu_dialog()

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
# CHAT CONTAINER — BUBBLE + TIMESTAMP
# =========================================================
_CHAT_HEIGHT = 600

_chat_container = st.container(height=_CHAT_HEIGHT, border=False)

with _chat_container:
    for _msg in st.session_state["yui_history"]:
        _role = _msg.get("role", "user")
        _time_msg = _msg.get("time", _now_jkt().strftime("%H:%M"))

        with st.chat_message(_role, avatar="👤" if _role == "user" else "📦"):
            st.markdown(_msg.get("content", ""))
            _align = "right" if _role == "user" else "left"
            st.markdown(
                f"<div class='bubble-time' style='text-align: {_align};'>"
                f"● {_time_msg}</div>",
                unsafe_allow_html=True,
            )

# =========================================================
# HELPER: EXPORT
# =========================================================
def _build_rekap_text_profesional(hasil, net_sales=0):
    _nom_hari = hasil.get("total_nominal", 0)
    _total_selisih_bulan = hasil.get("_total_selisih_bulan", 0)
    _total_rak_bulan = hasil.get("_total_rak_bulan", 0)

    _lines = [
        "=" * 50,
        "  LAPORAN STOCK OPNAME — TOKO C383",
        "=" * 50,
        f"Periode     : {hasil.get('periode', '-')}",
        f"Total Rak   : {hasil.get('total_rak', 0)} (periode ini)",
        f"Total Nominal: {fmt_rp_signed(_nom_hari)} (periode ini)",
        "",
    ]

    if net_sales > 0:
        from modules.yui_export import _hitung_btsb_nsb
        _calc = _hitung_btsb_nsb(net_sales, _total_selisih_bulan)
        _lines.extend([
            "-" * 50,
            "  ANALISIS BTSB & NSB (BULAN INI)",
            "-" * 50,
            f"Net Sales Bulan Ini : {fmt_rp(net_sales)}",
            f"BTSB (0,15%)        : {fmt_rp(_calc['btsb'])}",
            f"Total Selisih Bulan : {fmt_rp(_calc['selisih'])}",
            f"NSB (beban personil): {fmt_rp(_calc['nsb'])}",
            f"Status              : {_calc['status']}",
            f"Total Rak di-SO     : {_total_rak_bulan} rak",
            "",
        ])

    _lines.extend([
        "-" * 50,
        "  DETAIL PER RAK (PERIODE INI)",
        "-" * 50,
    ])

    for _r in hasil.get("list_rak", []):
        _lines.append(
            f"  {_r['rak_id']:8s} | {fmt_rp_signed(_r['total']):>15s} | PIC: {_r['pic']}"
        )

    _lines.extend([
        "",
        "=" * 50,
        "Keterangan:",
        "- NSB = (Net Sales x BTSB) - Total Selisih Barang (1 bulan)",
        "- BTSB = 0,15% dari Net Sales",
        "- Status OVER = selisih melebihi BTSB",
        "=" * 50,
    ])
    return "\n".join(_lines)


# =========================================================
# HELPER: SAVE & CLOSE
# =========================================================
def _save_and_close(edited_by_rak, pics_per_rak, pending_inner):
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

    st.session_state["yui_save_result"] = {
        "saved_count": _saved_count,
        "error_count": _error_count,
        "errors": _errors,
        "total": _total_nominal,
        "items": _total_items,
        "rak_saved_ids": list(edited_by_rak.keys()),
    }

    if _saved_count > 0:
        _success_msg = (
            f"🎉 **Beres Bos!** {_saved_count} rak tersimpan.\n"
            f"Total: **{fmt_rp_signed(_total_nominal)}**"
        )
        st.session_state["yui_history"].append({
            "role": "assistant", "content": _success_msg,
            "time": _now_jkt().strftime("%H:%M"),
        })
        save_message("yui", _session_id, "assistant", _success_msg)
        st.session_state["yui_pending_data"] = None
        st.cache_data.clear()
    else:
        _fail_msg = (
            f"❌ **Gagal simpan.** {_error_count} rak error.\n"
            + "\n".join([f"- {e}" for e in _errors[:5]])
        )
        st.session_state["yui_history"].append({
            "role": "assistant", "content": _fail_msg,
            "time": _now_jkt().strftime("%H:%M"),
        })
        save_message("yui", _session_id, "assistant", _fail_msg)

    st.rerun()

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
                "Tanggal SO", value=_now_jkt().date(), key="yui_file_tgl",
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
# PROCESS FILE
# =========================================================
if st.session_state.get("yui_file_to_process"):
    _fd = st.session_state["yui_file_to_process"]
    _file_name = _fd["name"]
    _file_bytes = _fd["bytes"]
    _tgl_ctx = _fd.get("tanggal")
    _rak_ctx = _fd.get("rak_id")

    yui_log(f"[Yui] Processing: {_file_name}")

    with _chat_container:
        with st.chat_message("assistant", avatar="📦"):
            st.markdown(f"📎 Aku baca **{_file_name}** dulu ya... ⏳")

    with st.spinner("📦 Yui baca file..."):
        _read_result = read_file(_file_bytes, _file_name,
                                 nama_personil="", bulan=None, tahun=None)

    yui_log(f"[Yui] Read: success={_read_result.get('success')}, type={_read_result.get('type')}")

    if not _read_result.get("success"):
        _err = f"❌ Gagal baca: {_read_result.get('error')}"
        with _chat_container:
            with st.chat_message("assistant", avatar="📦"):
                st.markdown(_err)
        st.session_state["yui_history"].append({
            "role": "assistant", "content": _err,
            "time": _now_jkt().strftime("%H:%M"),
        })
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
        with _chat_container:
            with st.chat_message("assistant", avatar="📦"):
                st.markdown(_fail)
        st.session_state["yui_history"].append({
            "role": "assistant", "content": _fail,
            "time": _now_jkt().strftime("%H:%M"),
        })
        save_message("yui", _session_id, "assistant", _fail)
        st.session_state["yui_file_to_process"] = None
        st.rerun()

    _data = _parse_result.get("data", {}) or {}
    _items = _data.get("items", [])
    _items_by_rak = _data.get("items_by_rak", {})
    _total_nom = _data.get("total_nominal", 0)
    _tanggal = _data.get("tanggal") or _tgl_ctx or _now_jkt().date().isoformat()

    if not _items_by_rak and _items:
        yui_log("[Yui] items_by_rak kosong, fallback grouping manual")
        _grouped = {}
        for _it in _items:
            _r = _it.get("rak_id") or "UNKNOWN"
            _grouped.setdefault(_r, []).append(_it)
        _items_by_rak = _grouped

    yui_log(f"[Yui] Extracted: {len(_items)} items, {len(_items_by_rak)} rak(s)")

    with _chat_container:
        with st.chat_message("assistant", avatar="📦"):
            _msg = f"✅ File **{_file_name}** berhasil aku baca!\n\n"
            _msg += f"📊 **Ringkasan:**\n"
            _msg += f"- 📅 Tanggal: **{_tanggal}**\n"
            _msg += f"- 🏪 Rak: **{len(_items_by_rak)} rak**\n"
            _msg += f"- 📦 Total item: **{len(_items)}**\n"
            _msg += f"- 💰 Total: **{fmt_rp(_total_nom)}**"
            st.markdown(_msg)

    st.session_state["yui_history"].append({
        "role": "assistant", "content": _msg,
        "time": _now_jkt().strftime("%H:%M"),
    })
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
# DIALOG REKAP SO
# =========================================================
@st.dialog("📊 Rekap SO", width="large")
def _dialog_rekap_so():
    if not _REKAP_OK:
        st.error("❌ Module yui_rekap gak ada")
        return

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

    _tgl_range = None
    if _mode == "custom":
        _tgl_range = st.date_input(
            "Rentang Tanggal",
            value=(_now_jkt().date(), _now_jkt().date()),
            key="rekap_range",
        )

    st.markdown("")
    _col_ok, _col_no = st.columns(2)
    with _col_ok:
        if st.button("🔍 TAMPILKAN", width="stretch", type="primary", key="btn_do_rekap"):
            _start = _end = None
            if _mode == "custom" and _tgl_range and len(_tgl_range) == 2:
                _start, _end = _tgl_range

            with st.spinner("📊 Yui rekap data..."):
                _hasil = rekap_so(mode=_mode, tgl_start=_start, tgl_end=_end)

            if _hasil.get("success"):
                st.session_state["yui_rekap_hasil"] = _hasil
                st.session_state["yui_show_rekap"] = False
                st.rerun()
            else:
                st.error(f"❌ {_hasil.get('error', 'Gagal rekap')}")
    with _col_no:
        if st.button("❌ BATAL", width="stretch", key="btn_cancel_rekap"):
            st.session_state["yui_show_rekap"] = False
            st.rerun()

_dialog_lain_kebuka = (
    st.session_state.get("yui_rak_to_delete") or
    st.session_state.get("yui_pending_data") or
    st.session_state.get("yui_save_result") or
    st.session_state.get("yui_show_upload") or
    st.session_state.get("yui_show_spd")
)

if st.session_state.get("yui_show_rekap") and not _dialog_lain_kebuka:
    _dialog_rekap_so()

# =========================================================
# DIALOG INPUT SPD
# =========================================================
@st.dialog("💰 Input SPD", width="large")
def _dialog_input_spd():
    st.markdown("**Input SPD hari ini**")
    st.caption("Yui bakal hitung budget SO otomatis (SPD × 0,15%)")

    _col_d, _col_spd = st.columns([1, 2])
    with _col_d:
        _tgl_spd = st.date_input("Tanggal", value=_now_jkt().date(), key="spd_tgl")
    with _col_spd:
        _spd_input = st.number_input(
            "Nominal SPD (Rp)",
            min_value=0, step=100000, value=0,
            key="spd_nominal", format="%d",
        )

    _budget_so = _spd_input * 0.0015
    st.markdown("---")
    _c_b1, _c_b2 = st.columns(2)
    with _c_b1:
        st.metric("💰 SPD INPUT", fmt_rp(_spd_input))
    with _c_b2:
        st.metric("🎯 BUDGET SO (0,15%)", fmt_rp(_budget_so))

    st.markdown("---")
    _c_ok, _c_no = st.columns(2)
    with _c_ok:
        if st.button("💾 SIMPAN SPD", width="stretch", type="primary",
                     key="btn_save_spd", disabled=(_spd_input <= 0)):
            try:
                _ok, _msg = save_spd_harian(_tgl_spd, _spd_input, "Input via Yui")
                if _ok:
                    _resp = (
                        f"✅ **SPD tersimpan!**\n\n"
                        f"- 📅 Tanggal: **{_tgl_spd}**\n"
                        f"- 💰 SPD: **{fmt_rp(_spd_input)}**\n"
                        f"- 🎯 Budget SO: **{fmt_rp(_budget_so)}** (0,15%)\n\n"
                        f"Gas input SO-nya Bos 🚀"
                    )
                    st.session_state["yui_history"].append({
                        "role": "assistant", "content": _resp,
                        "time": _now_jkt().strftime("%H:%M"),
                    })
                    save_message("yui", _session_id, "assistant", _resp)
                    st.session_state["yui_show_spd"] = False
                    st.cache_data.clear()
                    st.success("✅ SPD tersimpan!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"❌ {_msg}")
            except Exception as _e:
                st.error(f"❌ Error: {str(_e)[:100]}")
    with _c_no:
        if st.button("❌ BATAL", width="stretch", key="btn_cancel_spd"):
            st.session_state["yui_show_spd"] = False
            st.rerun()

_dialog_lain_untuk_spd = (
    st.session_state.get("yui_rak_to_delete") or
    st.session_state.get("yui_pending_data") or
    st.session_state.get("yui_save_result") or
    st.session_state.get("yui_show_rekap") or
    st.session_state.get("yui_show_upload")
)
if st.session_state.get("yui_show_spd") and not _dialog_lain_untuk_spd:
    _dialog_input_spd()


# =========================================================
# RENDER HASIL REKAP
# =========================================================
if st.session_state.get("yui_rekap_hasil"):
    _hasil_rekap = st.session_state["yui_rekap_hasil"]

    st.markdown("---")
    st.markdown("### 📊 Hasil Rekap SO")
    st.caption(f"Periode: {_hasil_rekap.get('periode', '-')}")

    _m1, _m2, _m3 = st.columns(3)
    with _m1:
        st.metric("🏪 Total Rak", _hasil_rekap.get("total_rak", 0))
    with _m2:
        st.metric("📦 Total Item", _hasil_rekap.get("total_item", 0))
    with _m3:
        _nom = _hasil_rekap.get("total_nominal", 0)
        st.metric("💰 Total Nominal", fmt_rp_signed(_nom))

    _list_rak = _hasil_rekap.get("list_rak", [])
    if _list_rak:
        with st.expander(f"📋 Detail {len(_list_rak)} Rak", expanded=True):
            _df_rak = pd.DataFrame(_list_rak)
            _df_rak = _df_rak.rename(columns={
                "rak_id": "Rak", "total": "Nominal",
                "pic": "PIC", "tanggal": "Tanggal",
            })
            st.dataframe(_df_rak, use_container_width=True, hide_index=True)

    _chart = _hasil_rekap.get("chart_data", [])
    if len(_chart) > 1:
        with st.expander("📈 Trend Per Hari", expanded=True):
            _df_chart = pd.DataFrame(_chart)
            st.bar_chart(_df_chart.set_index("tanggal")[["nominal"]],
                         use_container_width=True)
    elif len(_chart) == 1:
        st.caption(f"📊 Cuma 1 hari data: {_chart[0]['tanggal']}")

    # =========================================================
    # EXPORT BUTTONS
    # =========================================================
    st.markdown("#### 📥 Export Laporan")
    _c_exp1, _c_exp2, _c_exp3, _c_exp4 = st.columns(4)

    _net_sales_bulan = 0
    _total_selisih_bulan = 0
    _total_rak_bulan = 0

    try:
        from modules.yui_rekap import (
            _get_net_sales_bulan, _get_total_selisih_bulan, _get_total_rak_bulan
        )
        _net_sales_bulan = _get_net_sales_bulan()
        _total_selisih_bulan = _get_total_selisih_bulan()
        _total_rak_bulan = _get_total_rak_bulan()
    except Exception:
        pass

    _hasil_rekap["_net_sales_bulan"] = _net_sales_bulan
    _hasil_rekap["_total_selisih_bulan"] = _total_selisih_bulan
    _hasil_rekap["_total_rak_bulan"] = _total_rak_bulan

    with _c_exp1:
        if st.button("📄 PDF", width="stretch", key="btn_exp_pdf"):
            _hasil_for_export = st.session_state.get("_last_hasil_rekap") or st.session_state.get("yui_rekap_hasil")
            if not _hasil_for_export:
                st.error("❌ Data rekap hilang. Coba rekap ulang.")
            elif not _EXPORT_OK:
                st.error("❌ Module yui_export gak ada")
            else:
                with st.spinner("Bikin PDF..."):
                    try:
                        _pdf_bytes = export_rekap_pdf(_hasil_for_export)
                        if _pdf_bytes and _pdf_bytes.startswith(b"ERROR:"):
                            _err_text = _pdf_bytes.decode("utf-8", errors="replace")
                            st.error(f"❌ PDF Error dari yui_export:\n\n```\n{_err_text[:1500]}\n```")
                        elif _pdf_bytes and len(_pdf_bytes) > 500:
                            st.session_state["yui_export_result"] = {
                                "type": "pdf",
                                "bytes": _pdf_bytes,
                                "filename": f"laporan_so_{_hasil_for_export['periode'].replace(' ', '_')}.pdf",
                            }
                            st.rerun()
                        else:
                            st.error("❌ Gagal bikin PDF. Hasil kosong.")
                    except Exception as _e_pdf:
                        import traceback
                        st.error(f"❌ Exception di export_rekap_pdf: {type(_e_pdf).__name__}: {str(_e_pdf)[:300]}")
                        st.code(traceback.format_exc(), language="python")

    with _c_exp2:
        if st.button("📊 Excel", width="stretch", key="btn_exp_xlsx"):
            _xlsx_bytes = None
            try:
                from modules.yui_export import export_rekap_excel
                _xlsx_bytes = export_rekap_excel(_hasil_rekap, net_sales=_net_sales_bulan)
            except Exception as _e:
                st.error(f"❌ {str(_e)[:100]}")
            if _xlsx_bytes:
                st.session_state["yui_export_result"] = {
                    "type": "xlsx",
                    "bytes": _xlsx_bytes,
                    "filename": f"laporan_so_{_hasil_rekap['periode'].replace(' ', '_')}.xlsx",
                }
                st.rerun()
            else:
                st.error("❌ Gagal bikin Excel")

    with _c_exp3:
        if st.button("📋 Text", width="stretch", key="btn_exp_text"):
            _text = _build_rekap_text_profesional(_hasil_rekap, net_sales=_net_sales_bulan)
            st.session_state["yui_export_result"] = {
                "type": "text",
                "text": _text,
                "filename": "laporan_so.txt",
            }
            st.rerun()

    with _c_exp4:
        if st.button("📸 Gambar", width="stretch", key="btn_exp_img"):
            if not _EXPORT_OK:
                st.error("❌ Module yui_export gak ada")
            else:
                with st.spinner("Bikin gambar..."):
                    _img_path = export_rekap_image(_hasil_rekap, net_sales=_net_sales_bulan)
                if _img_path:
                    try:
                        with open(_img_path, "rb") as _f:
                            _img_bytes = _f.read()
                        st.session_state["yui_export_result"] = {
                            "type": "png",
                            "bytes": _img_bytes,
                            "filename": f"laporan_so_{_hasil_rekap['periode'].replace(' ', '_')}.png",
                        }
                        st.rerun()
                    except Exception as _e:
                        st.error(f"❌ {str(_e)[:80]}")
                else:
                    st.error("❌ Gagal bikin gambar. Cek `html2pic` di requirements.")

    # TAMPILKAN HASIL EXPORT
    if st.session_state.get("yui_export_result"):
        _exp = st.session_state["yui_export_result"]
        st.markdown("---")
        st.markdown("##### 📥 File Siap Di-Download")

        if _exp["type"] == "text":
            st.code(_exp["text"], language="text")
            _wa_link = _build_wa_link(_exp["text"])
            st.markdown("")
            st.markdown(
                f"<a href='{_wa_link}' target='_blank' "
                f"style='display:inline-block; padding:12px 24px; "
                f"background:#25D366; color:white; text-decoration:none; "
                f"border-radius:8px; font-weight:bold; font-size:14px;'>"
                f"📱 Kirim ke WhatsApp</a>",
                unsafe_allow_html=True,
            )
            st.caption("💡 Klik tombol di atas buat buka WhatsApp dengan pesan yang udah ke-isi.")
        elif _exp["type"] == "png":
            st.image(_exp["bytes"], caption=_exp["filename"])
            st.download_button(
                "📥 Download Gambar", data=_exp["bytes"],
                file_name=_exp["filename"], mime="image/png",
                key="dl_export_png", type="primary",
            )
        elif _exp["type"] == "pdf":
            st.download_button(
                "📥 Download PDF", data=_exp["bytes"],
                file_name=_exp["filename"], mime="application/pdf",
                key="dl_export_pdf", type="primary",
            )
        elif _exp["type"] == "xlsx":
            st.download_button(
                "📥 Download Excel", data=_exp["bytes"],
                file_name=_exp["filename"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_export_xlsx", type="primary",
            )

        if st.button("❌ Tutup Export", key="btn_close_export"):
            st.session_state["yui_export_result"] = None
            st.rerun()

    if st.button("❌ Tutup Rekap", key="btn_close_rekap", width="stretch"):
        st.session_state["yui_rekap_hasil"] = None
        st.session_state["yui_export_result"] = None
        st.rerun()
        
# =========================================================
# KONFIRMASI MULTI-RAK + MULTI-PIC
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
                                options=_pic_options, index=_pic_idx,
                                key=f"pic_rak_{_rak_id}",
                            )
                            if _new_pic:
                                _pics_per_rak[_rak_id] = _new_pic
                        else:
                            _new_pic = st.text_input(
                                f"👤 PIC untuk {_rak_id}",
                                placeholder="Nama PIC", key=f"pic_rak_{_rak_id}",
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
                        "plu": "PLU", "nama_produk": "Nama Produk",
                        "qty_sistem": "Qty Sistem", "qty_fisik": "Qty Fisik",
                        "qty_var": "Qty Var", "nominal_adjust": "Nominal",
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
                        use_container_width=True, hide_index=True,
                        num_rows="dynamic",
                        height=min(400, 80 + len(_df_rak) * 38),
                        column_config={
                            "PLU": st.column_config.TextColumn("PLU", width="small"),
                            "Nama Produk": st.column_config.TextColumn("Nama Produk", width="large"),
                            "Qty Sistem": st.column_config.NumberColumn("Qty Sistem", width="small"),
                            "Qty Fisik": st.column_config.NumberColumn("Qty Fisik", width="small"),
                            "Qty Var": st.column_config.NumberColumn(
                                "Qty Var", width="small", disabled=True,
                                help="Auto: Qty Fisik − Qty Sistem"),
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
            f"<div class='metric-clean' style='border-left-color: {_total_color}; "
            f"text-align: right; margin-top: 16px;'>"
            f"<div class='label'>💰 TOTAL SEMUA</div>"
            f"<div class='value' style='color: {_total_color};'>{fmt_rp_signed(_new_total)}</div>"
            f"</div>", unsafe_allow_html=True,
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
                st.session_state["yui_history"].append({
                    "role": "assistant", "content": _cancel,
                    "time": _now_jkt().strftime("%H:%M"),
                })
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
                f"{fmt_rp_signed(_total)}</div></div>", unsafe_allow_html=True,
            )
            _rak_str = ", ".join(_rak_ids) if _rak_ids else "-"
            st.caption(f"🏪 Rak tersimpan: **{_rak_str}**")
        elif _saved > 0 and _errors > 0:
            st.warning(f"⚠️ **{_saved} rak tersimpan**, {_errors} rak gagal.")
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


# =========================================================
# CHAT HANDLER — LOGIC TETAP SAMA
# =========================================================
if _user_msg:
    _time_now = _now_jkt().strftime("%H:%M")

    st.session_state["yui_history"].append({
        "role": "user", "content": _user_msg, "time": _time_now,
    })
    save_message("yui", _session_id, "user", _user_msg)

    with _chat_container:
        with st.chat_message("user", avatar="👤"):
            st.markdown(_user_msg)
            st.markdown(
                f"<div class='bubble-time' style='text-align: right;'>"
                f"● {_time_now}</div>",
                unsafe_allow_html=True,
            )

    _user_lower = _user_msg.lower().strip()

    # === INTENT DETECTION (SAMA KAYAK SEBELUMNYA) ===
    _is_rekap = any(kw in _user_lower for kw in [
        "rekap", "rangkum", "summary", "ringkas", "total so", "list rak",
    ])
    _is_list_item = any(kw in _user_lower for kw in [
        "list item", "rekap item", "item minus", "item plus", "item di rak",
    ])
    _is_spd_input = (
        ("spd" in _user_lower and any(k in _user_lower for k in ["input", "catat", "simpan", "tambah"]))
        or ("spd" in _user_lower and bool(re.search(r'\d{3,}', _user_lower.replace(".", "").replace(",", ""))))
    )
    _is_input_so = (
        any(kw in _user_lower for kw in ["input so", "catat so", "tambah so", "minus", "plus", "selisih"])
        or bool(re.search(r'\d+\s*(rb|ribu|jt|juta|k)\b', _user_lower))
        or bool(re.search(r'rp\s*\d', _user_lower))
    )

    if _is_rekap or _is_list_item or _is_spd_input:
        _is_input_so = False

    # === HELPER: PARSER TANGGAL RANGE (SAMA) ===
    def _parse_tanggal_range(text):
        from datetime import date, timedelta
        _now = _now_jkt().date()
        _text = text.lower()

        _match_range = re.search(
            r'(\d{1,2})\s*[-–]\s*(\d{1,2})\s*(oktober|okt|november|nov|desember|des|'
            r'januari|jan|februari|feb|maret|mar|april|apr|mei|juni|jun|juli|jul|'
            r'agustus|agu|ags|september|sep)?',
            _text,
        )
        if _match_range:
            _d1 = int(_match_range.group(1))
            _d2 = int(_match_range.group(2))
            _bulan_str = _match_range.group(3)
            _bulan_map = {
                "januari": 1, "jan": 1, "februari": 2, "feb": 2,
                "maret": 3, "mar": 3, "april": 4, "apr": 4,
                "mei": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7,
                "agustus": 8, "agu": 8, "ags": 8,
                "september": 9, "sep": 9, "oktober": 10, "okt": 10,
                "november": 11, "nov": 11, "desember": 12, "des": 12,
            }
            _bulan = _bulan_map.get(_bulan_str, _now.month) if _bulan_str else _now.month
            try:
                _start = date(_now.year, _bulan, _d1)
                _end = date(_now.year, _bulan, _d2)
                return _start, _end
            except Exception:
                pass

        _match_single = re.search(
            r'(\d{1,2})\s*(oktober|okt|november|nov|desember|des|januari|jan|'
            r'februari|feb|maret|mar|april|apr|mei|juni|jun|juli|jul|'
            r'agustus|agu|ags|september|sep)?\s*(\d{4})?',
            _text,
        )
        if _match_single:
            _d = int(_match_single.group(1))
            _bulan_str = _match_single.group(2)
            _tahun_str = _match_single.group(3)
            _bulan_map = {
                "januari": 1, "jan": 1, "februari": 2, "feb": 2,
                "maret": 3, "mar": 3, "april": 4, "apr": 4,
                "mei": 5, "juni": 6, "jun": 6, "juli": 7, "jul": 7,
                "agustus": 8, "agu": 8, "ags": 8,
                "september": 9, "sep": 9, "oktober": 10, "okt": 10,
                "november": 11, "nov": 11, "desember": 12, "des": 12,
            }
            _bulan = _bulan_map.get(_bulan_str, _now.month) if _bulan_str else _now.month
            _tahun = int(_tahun_str) if _tahun_str else _now.year
            try:
                _tgl = date(_tahun, _bulan, _d)
                return _tgl, _tgl
            except Exception:
                pass

        return None, None

    def _ekstrak_rak(text):
        _match = re.search(r'\b([A-Za-z]{1,3}\d{1,4}|\d{3,4})\b', text.upper())
        if _match:
            return _match.group(1)
        return None

    # === RESPONSE (LOGIC TETAP SAMA) ===
    with _chat_container:
        with st.chat_message("assistant", avatar="📦"):
            with st.spinner("📦 Aku cek..."):

                # --- INPUT SPD ---
                if _is_spd_input:
                    _nom_match = re.search(r'(\d[\d.,]*)\s*(jt|juta|rb|ribu|k)?', _user_lower)
                    _nominal = 0
                    if _nom_match:
                        _raw = _nom_match.group(1).replace(".", "").replace(",", "")
                        try:
                            _nominal = int(_raw)
                            _suffix = _nom_match.group(2)
                            if _suffix in ("jt", "juta"):
                                _nominal *= 1_000_000
                            elif _suffix in ("rb", "ribu", "k"):
                                _nominal *= 1_000
                        except Exception:
                            _nominal = 0

                    if _nominal > 0:
                        _budget = _nominal * 0.0015
                        _resp = (
                            f"💰 **Konfirmasi Input SPD**\n\n"
                            f"- 📅 Tanggal: **{_now_jkt().date()}**\n"
                            f"- 💵 SPD: **{fmt_rp(_nominal)}**\n"
                            f"- 🎯 Budget SO (0,15%): **{fmt_rp(_budget)}**\n\n"
                            f"Ketik **`spd oke`** buat simpan, atau **`spd batal`** buat batal."
                        )
                        st.markdown(_resp)
                        st.session_state["yui_history"].append({
                            "role": "assistant", "content": _resp,
                            "time": _now_jkt().strftime("%H:%M"),
                        })
                        save_message("yui", _session_id, "assistant", _resp)
                        st.session_state["yui_pending_spd"] = _nominal
                    else:
                        _resp = "❌ Gak nemu nominal SPD. Contoh: `input spd hari ini 12.750.800`"
                        st.markdown(_resp)
                        st.session_state["yui_history"].append({
                            "role": "assistant", "content": _resp,
                            "time": _now_jkt().strftime("%H:%M"),
                        })
                        save_message("yui", _session_id, "assistant", _resp)

                # --- KONFIRMASI SPD ---
                elif _user_lower in ("spd oke", "spd ok", "spd simpan"):
                    _spd_val = st.session_state.get("yui_pending_spd", 0)
                    if _spd_val > 0:
                        try:
                            _ok, _msg = save_spd_harian(_now_jkt().date(), _spd_val, "Input via Yui chat")
                            _resp = f"✅ SPD **{fmt_rp(_spd_val)}** tersimpan Bos!" if _ok else f"❌ Gagal: {_msg}"
                        except Exception as _e:
                            _resp = f"❌ Error: {str(_e)[:100]}"
                        st.session_state["yui_pending_spd"] = None
                    else:
                        _resp = "❌ Gak ada SPD pending."
                    st.markdown(_resp)
                    st.session_state["yui_history"].append({
                        "role": "assistant", "content": _resp,
                        "time": _now_jkt().strftime("%H:%M"),
                    })
                    save_message("yui", _session_id, "assistant", _resp)

                elif _user_lower in ("spd batal", "spd cancel"):
                    st.session_state["yui_pending_spd"] = None
                    _resp = "Oke Bos, SPD dibatalkan."
                    st.markdown(_resp)
                    st.session_state["yui_history"].append({
                        "role": "assistant", "content": _resp,
                        "time": _now_jkt().strftime("%H:%M"),
                    })
                    save_message("yui", _session_id, "assistant", _resp)

                # --- LIST ITEM ---
                elif _is_list_item:
                    try:
                        from modules.supabase_client import get_supabase
                        from modules.yui_rekap import get_top_items
                        from datetime import date, timedelta

                        _sb = get_supabase()
                        _rak_filter = _ekstrak_rak(_user_lower)
                        _tgl_start, _tgl_end = _parse_tanggal_range(_user_lower)

                        if _tgl_start is None:
                            _tgl_start = _now_jkt().date()
                            _tgl_end = _tgl_start

                        if _rak_filter:
                            _res = (
                                _sb.table("so_hasil")
                                .select("*")
                                .eq("rak_id", _rak_filter)
                                .gte("so_date", _tgl_start.isoformat())
                                .lte("so_date", _tgl_end.isoformat())
                                .execute()
                            )
                            _rows = _res.data or []

                            if not _rows:
                                _resp = f"📭 Gak ada item di rak **{_rak_filter}** periode {_tgl_start} s/d {_tgl_end}."
                            else:
                                _rows_sorted = sorted(_rows, key=lambda x: float(x.get("nominal_adjust", 0) or 0))
                                _total = sum(float(r.get("nominal_adjust", 0) or 0) for r in _rows)
                                _resp = f"📦 **Item RAK {_rak_filter}** ({_tgl_start} s/d {_tgl_end})\n\n"
                                _resp += f"Total: **{len(_rows)} item** • **{fmt_rp_signed(_total)}**\n\n"
                                for _r in _rows_sorted[:20]:
                                    _nom = float(_r.get("nominal_adjust", 0) or 0)
                                    _resp += f"- `{_r.get('plu', '-')}` {str(_r.get('nama_produk', '-'))[:35]}: **{fmt_rp_signed(_nom)}**\n"
                                if len(_rows_sorted) > 20:
                                    _resp += f"\n... +{len(_rows_sorted) - 20} item lainnya"

                        elif "minus" in _user_lower or "plus" in _user_lower:
                            _top = get_top_items(limit=5)
                            _key = "top_minus" if "minus" in _user_lower else "top_plus"
                            _items = _top.get(_key, [])

                            if not _items:
                                _resp = f"📭 Gak ada item {'minus' if 'minus' in _user_lower else 'plus'} di periode ini."
                            else:
                                _resp = f"📊 **Top 5 Item {'Minus' if 'minus' in _user_lower else 'Plus'} Tertinggi**\n\n"
                                for _i, _it in enumerate(_items, 1):
                                    _nom = float(_it.get("nominal_adjust", 0) or 0)
                                    _resp += f"{_i}. `{_it.get('plu', '-')}` {str(_it.get('nama_produk', '-'))[:30]}\n"
                                    _resp += f"   Rak **{_it.get('rak_id', '-')}** • **{fmt_rp_signed(_nom)}**\n"

                        else:
                            _resp = "❓ Bos, aku bisa bantu list item dengan command:\n\n"
                            _resp += "- `list item minus tertinggi`\n"
                            _resp += "- `list item plus tertinggi`\n"
                            _resp += "- `list item di rak S11`\n"
                            _resp += "- `list item tanggal 10-12`\n"

                    except Exception as _e:
                        _resp = f"❌ Error: {str(_e)[:150]}"

                    st.markdown(_resp)
                    st.session_state["yui_history"].append({
                        "role": "assistant", "content": _resp,
                        "time": _now_jkt().strftime("%H:%M"),
                    })
                    save_message("yui", _session_id, "assistant", _resp)

                # --- REKAP ---
                elif _is_rekap:
                    _mode = "hari_ini"
                    _tgl_start, _tgl_end = _parse_tanggal_range(_user_lower)

                    if _tgl_start and _tgl_end and _tgl_start != _tgl_end:
                        _mode = "custom"
                    elif _tgl_start and _tgl_end and _tgl_start == _tgl_end:
                        _mode = "custom"
                    elif "minggu" in _user_lower:
                        _mode = "minggu_ini"
                    elif "bulan" in _user_lower:
                        _mode = "bulan_ini"

                    try:
                        _hasil = rekap_so(
                            mode=_mode,
                            tgl_start=_tgl_start if _mode == "custom" else None,
                            tgl_end=_tgl_end if _mode == "custom" else None,
                        )
                        if _hasil.get("success"):
                            _nom = _hasil["total_nominal"]
                            _resp = f"📊 **Rekap SO ({_hasil['periode']})**\n\n"
                            _resp += f"- 🏪 Total rak: **{_hasil['total_rak']}**\n"
                            _resp += f"- 📦 Total item: **{_hasil['total_item']}**\n"
                            _resp += f"- 💰 Total nominal: **{fmt_rp_signed(_nom)}**\n"

                            _list_rak = _hasil.get("list_rak", [])
                            if _list_rak:
                                _resp += f"\n**Detail per rak:**\n"
                                for _r in _list_rak[:10]:
                                    _resp += f"- 🏪 {_r['rak_id']}: {fmt_rp_signed(_r['total'])} (PIC: {_r['pic']})\n"
                                if len(_list_rak) > 10:
                                    _resp += f"... +{len(_list_rak) - 10} rak lainnya\n"

                            _resp += f"\n💡 Mau analisis? Tanya Rei aja Bos 😏"
                            st.session_state["yui_rekap_hasil"] = _hasil
                        else:
                            _resp = f"❌ Gagal rekap: {_hasil.get('error', 'unknown')}"
                    except Exception as _e:
                        _resp = f"❌ Error rekap: {str(_e)[:100]}"

                    st.markdown(_resp)
                    st.session_state["yui_history"].append({
                        "role": "assistant", "content": _resp,
                        "time": _now_jkt().strftime("%H:%M"),
                    })
                    save_message("yui", _session_id, "assistant", _resp)

                # --- INPUT SO ---
                elif _is_input_so:
                    _parse = parse_natural_language(_user_msg, _rak_list[:100])
                    if _parse.get("success") and _parse.get("data"):
                        _data = _parse["data"]
                        _items = _data.get("items", [])
                        _tanggal = _data.get("tanggal", _now_jkt().date().isoformat())
                        _total = sum(float(i.get("nominal_adjust", 0) or 0) for i in _items)

                        _resp = f"📦 Oke Bos, aku catat:\n\n- 📅 {_tanggal}\n"
                        for _item in _items:
                            _nom = float(_item.get("nominal_adjust", 0) or 0)
                            _resp += f"- 🏪 **{_item.get('rak_id', '?')}**: {fmt_rp_signed(_nom)}\n"
                        _resp += f"\n💰 Total: **{fmt_rp_signed(_total)}**"

                        st.markdown(_resp)
                        st.session_state["yui_history"].append({
                            "role": "assistant", "content": _resp,
                            "time": _now_jkt().strftime("%H:%M"),
                        })
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
                        st.session_state["yui_history"].append({
                            "role": "assistant", "content": _resp,
                            "time": _now_jkt().strftime("%H:%M"),
                        })
                        save_message("yui", _session_id, "assistant", _resp)

                # --- CHAT BIASA ---
                else:
                    _chat = yui_chat(_user_msg, st.session_state["yui_history"])
                    _resp = _chat.get("text", "")
                    st.markdown(_resp)
                    st.session_state["yui_history"].append({
                        "role": "assistant", "content": _resp,
                        "time": _now_jkt().strftime("%H:%M"),
                    })
                    save_message("yui", _session_id, "assistant", _resp)

    st.rerun()


# =========================================================
# FOOTER TIPIS
# =========================================================
_total_msg = len(st.session_state["yui_history"])
_model_str = "yui"

st.markdown(
    f"<div class='memory-info-footer'>"
    f"🧠 Session: <code style='color: #7FB99B;'>{_session_id[-12:]}</code> | "
    f"💬 <b style='color: #F5E6D3;'>{_total_msg}</b> pesan | "
    f"⚙️ <b style='color: #7FB99B;'>{_model_str}</b>"
    f"</div>",
    unsafe_allow_html=True,
)