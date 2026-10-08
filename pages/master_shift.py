"""
Master Shift Page v2
====================
Struktur baru:
- 🌸 Hana       (all-in-one chat: Q&A + update + delete + konfirmasi)
- 📸 Screenshot (OCR kalender)
- 📊 Matrix     (sub-tab: tabel master | personil | download)
- 📈 Usage      (monitoring token)
"""

import streamlit as st
import pandas as pd
import time
import io
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from PIL import Image as PILImage

from themes.theme_loader import (
    render_theme,
    render_theme_animations,
    render_greeting,
    get_theme_by_month,
)

# =========================================================================
# KONFIGURASI
# =========================================================================
st.set_page_config(
    page_title="Master Shift | Toko C383",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CURRENT_THEME = get_theme_by_month()
render_theme(CURRENT_THEME)
render_theme_animations(CURRENT_THEME)
render_greeting()

# =========================================================================
# IMPORT
# =========================================================================
try:
    from modules.master_shift_handler import (
        load_personil_master,
        add_personil,
        update_personil_status,
        save_master_shift,
        load_master_shift_matrix,
        get_shift_hari_ini,
        generate_master_shift_excel,
        delete_shift_by_name,      # ✅ FIX C4: dipake buat hapus per tanggal
        delete_shift_all_dates,    # ✅ FIX C4: dipake buat hapus semua tanggal
        KODE_SHIFT,
        NAMA_BULAN_ID,
    )
    from modules.ai_shift_manager import (
        chat_response,
        parse_shift_update,
        ai_suggest_pengganti_text,
        ai_check_conflict_text,
    )
except ImportError as e:
    st.error(f"❌ Gagal import module: {e}")
    st.stop()


# =========================================================================
# CSS CUSTOM — PILL TAB
# =========================================================================
def inject_pill_css():
    st.markdown("""
    <style>
        div[data-testid="stHorizontalBlock"] > div > div > div > button[kind="secondary"],
        div[data-testid="stHorizontalBlock"] > div > div > div > button[kind="primary"] {
            border-radius: 999px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            padding: 0.5rem 1rem !important;
            transition: all 0.2s ease !important;
            border-width: 1.5px !important;
        }
        
        div[data-testid="stHorizontalBlock"] > div > div > div > button[kind="primary"] {
            box-shadow: 0 0 15px rgba(232, 177, 137, 0.5) !important;
            transform: translateY(-1px) !important;
        }
    </style>
    """, unsafe_allow_html=True)


inject_pill_css()


# =========================================================================
# HEADER
# =========================================================================
def render_header():
    _now = datetime.now(ZoneInfo("Asia/Jakarta"))
    _time_str = _now.strftime("%H:%M")

    _day_map = {"Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
                "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"}
    _month_map = {"January": "Januari", "February": "Februari", "March": "Maret",
                  "April": "April", "May": "Mei", "June": "Juni", "July": "Juli",
                  "August": "Agustus", "September": "September", "October": "Oktober",
                  "November": "November", "December": "Desember"}
    _day_id = _day_map.get(_now.strftime("%A"), _now.strftime("%A"))
    _month_id = _month_map.get(_now.strftime("%B"), _now.strftime("%B"))
    _date_id = f"{_day_id}, {_now.day} {_month_id} {_now.year}"

    st.markdown(
        "<div class='royal-header fade-in-up'>"
        "<div class='royal-title'>🌸 MASTER SHIFT 🌸</div>"
        "<div class='royal-subtitle'>⚜ Hana — Asisten Jadwal Toko C383 ⚜</div>"
        "<div class='header-clock'>"
        f"<div class='clock-time'>🕐 {_time_str} WIB</div>"
        f"<div class='clock-date'>📅 {_date_id}</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


render_header()

# Back button
_col_back, _ = st.columns([1, 4])
with _col_back:
    if st.button("← Dashboard", key="btn_back_home", width="stretch"):
        try:
            st.switch_page("Dashboard.py")
        except Exception:
            pass


# =========================================================================
# TAB NAVIGATION — PILL
# =========================================================================
if "ms_tab" not in st.session_state:
    st.session_state["ms_tab"] = "hana"

_TABS = [
    ("hana", "🌸 Hana"),
    ("screenshot", "📸 Screenshot"),
    ("matrix", "📊 Matrix"),
    ("usage", "📈 Usage"),
]

_cols = st.columns(len(_TABS))
for _i, (_key, _label) in enumerate(_TABS):
    with _cols[_i]:
        _is_active = st.session_state["ms_tab"] == _key
        if st.button(
            _label,
            key=f"ms_tab_btn_{_key}",
            width="stretch",
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["ms_tab"] = _key
            st.rerun()

st.markdown("---")
# =========================================================================
# TAB 1: HANA (CHAT + UPDATE + DELETE)
# =========================================================================
def render_hana():
    """Tab Hana — chat all-in-one."""

    # Init chat history
    if "hana_history" not in st.session_state:
        st.session_state["hana_history"] = []

    if "hana_pending_update" not in st.session_state:
        st.session_state["hana_pending_update"] = None

    if "hana_last_saved" not in st.session_state:
        st.session_state["hana_last_saved"] = None

    # Notifikasi update berhasil
    if st.session_state["hana_last_saved"]:
        st.success(st.session_state["hana_last_saved"])
        st.session_state["hana_last_saved"] = None

    # Header chat room
    st.markdown("### 🌸 Hana")
    st.caption("Tanya jadwal, minta update, atau minta rekomendasi pengganti. Hana siap bantu!")

    # Contoh perintah (quick action)
    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        if st.button("📅 Jadwal hari ini?", width="stretch", key="hana_qa1"):
            st.session_state["hana_preset"] = "Jadwal hari ini?"
    with _c2:
        if st.button("👤 Siapa libur?", width="stretch", key="hana_qa2"):
            st.session_state["hana_preset"] = "Siapa aja yang libur hari ini?"
    with _c3:
        if st.button("🔄 Atur Reza ke siang", width="stretch", key="hana_qa3"):
            st.session_state["hana_preset"] = "Atur Reza ke shift siang ya"

    st.markdown("---")

    # === RENDER HISTORY CHAT ===
    for _msg in st.session_state["hana_history"]:
        _role = _msg.get("role", "user")
        _content = _msg.get("content", "")
        with st.chat_message(_role, avatar="👤" if _role == "user" else "🌸"):
            st.markdown(_content)

    # =====================================================================
    # ✅ FIX C4: PENDING UPDATE PREVIEW — Handle UPDATE & DELETE mode
    # =====================================================================
    if st.session_state["hana_pending_update"]:
        _parsed = st.session_state["hana_pending_update"]
        _mode = _parsed.get("mode", "update")

        # -----------------------------------------------------------------
        # ✅ FIX C4: MODE DELETE (BARU — sebelumnya gak di-handle!)
        # -----------------------------------------------------------------
        if _mode == "delete":
            _delete_targets = _parsed.get("delete_targets", [])
            _delete_all_dates = _parsed.get("delete_all_dates", False)

            st.markdown("#### 🗑️ Preview Hapus Shift")

            # Warning info
            if _delete_all_dates:
                st.warning(
                    f"⚠️ Akan hapus **SEMUA shift** untuk: "
                    f"**{', '.join(_delete_targets)}**"
                )
            else:
                _tgl_list = _parsed.get("tanggal_list", [_parsed.get("tanggal")])
                _tgl_str = ", ".join([t.strftime("%d/%m/%Y") for t in _tgl_list])
                st.warning(
                    f"⚠️ Akan hapus shift **{', '.join(_delete_targets)}** "
                    f"untuk: {_tgl_str}"
                )

            # Tombol konfirmasi & batal
            _col1, _col2 = st.columns(2)
            with _col1:
                if st.button(
                    "✅ KONFIRMASI HAPUS",
                    width="stretch",
                    type="primary",
                    key="btn_hana_delete",
                ):
                    _total_deleted = 0

                    if _delete_all_dates:
                        # Hapus semua tanggal
                        for _nama in _delete_targets:
                            _ok, _msg = delete_shift_all_dates(_nama)
                            if _ok:
                                _total_deleted += 1
                    else:
                        # Hapus per tanggal
                        for _tgl_hapus in _parsed.get("tanggal_list", [_parsed.get("tanggal")]):
                            _ok, _msg, _detail = delete_shift_by_name(_tgl_hapus, _delete_targets)
                            if _ok:
                                _total_deleted += _detail.get("deleted", 0)

                    if _total_deleted > 0:
                        st.session_state["hana_last_saved"] = f"🗑️ {_total_deleted} shift dihapus!"
                        st.session_state["hana_history"].append({
                            "role": "assistant",
                            "content": f"🗑️ Sip! **{_total_deleted} shift** udah Hana hapus 🌸",
                        })
                        st.session_state["hana_pending_update"] = None
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Gagal hapus shift")

            with _col2:
                if st.button(
                    "❌ BATAL",
                    width="stretch",
                    key="btn_hana_cancel_delete",
                ):
                    st.session_state["hana_history"].append({
                        "role": "assistant",
                        "content": "Oke, gak jadi hapus ya! 🌸",
                    })
                    st.session_state["hana_pending_update"] = None
                    st.rerun()

            st.markdown("---")
            return  # ← Stop, jangan render preview shift_map di bawah

        # -----------------------------------------------------------------
        # MODE UPDATE (EXISTING — gak berubah)
        # -----------------------------------------------------------------
        _shift_map = _parsed.get("shift_map", {})
        _tgl_list = _parsed.get("tanggal_list", [_parsed["tanggal"]])

        if _shift_map:
            st.markdown("#### 📊 Preview Perubahan")

            _preview_rows = []
            for _nama, _kode in _shift_map.items():
                _info = KODE_SHIFT.get(_kode, {"label": "-", "icon": "❓"})
                for _tgl in _tgl_list:
                    _preview_rows.append({
                        "👤 Nama": _nama,
                        "📅 Tanggal": _tgl.strftime("%d/%m/%Y"),
                        "🔄 Kode": _kode,
                        "📋 Ket.": _info["label"],
                    })
            st.dataframe(pd.DataFrame(_preview_rows), width="stretch", hide_index=True)

            _catatan = st.text_input(
                "📝 Catatan (opsional)",
                placeholder="Contoh: Ganti dadakan",
                key="hana_catatan",
            )

            _col1, _col2 = st.columns(2)
            with _col1:
                if st.button(
                    "✅ KONFIRMASI SIMPAN",
                    width="stretch",
                    type="primary",
                    key="btn_hana_save",
                ):
                    _total = 0
                    for _tgl_save in _tgl_list:
                        _ok, _msg = save_master_shift(
                            tanggal=_tgl_save,
                            shift_map=_shift_map,
                            sumber="hana_chat",
                            catatan=f"{_catatan} | Chat: {_parsed.get('raw_text', '')[:100]}",
                        )
                        if _ok:
                            _total += len(_shift_map)

                    if _total > 0:
                        _nama_updated = ", ".join(_shift_map.keys())
                        st.session_state["hana_last_saved"] = (
                            f"✅ **{_total} shift** berhasil disimpan! "
                            f"({_nama_updated}) — Dashboard bakal update."
                        )
                        st.session_state["hana_history"].append({
                            "role": "assistant",
                            "content": f"✅ Sip! **{_total} shift** udah Hana simpan 🌸 "
                                       f"({_nama_updated}). Cek dashboard ya!",
                        })
                        st.session_state["hana_pending_update"] = None
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Gagal simpan")

            with _col2:
                if st.button(
                    "❌ BATAL",
                    width="stretch",
                    key="btn_hana_cancel",
                ):
                    st.session_state["hana_history"].append({
                        "role": "assistant",
                        "content": "Oke, gak jadi update ya! 🌸",
                    })
                    st.session_state["hana_pending_update"] = None
                    st.rerun()

    # === INPUT CHAT ===
    _preset = st.session_state.pop("hana_preset", "")
    _user_msg = st.chat_input("Tanya atau perintah Hana...", key="hana_chat_input")

    if _preset and not _user_msg:
        _user_msg = _preset

    if _user_msg:
        # Simpan user message
        st.session_state["hana_history"].append({"role": "user", "content": _user_msg})

        with st.chat_message("user", avatar="👤"):
            st.markdown(_user_msg)

        # Get response Hana
        with st.chat_message("assistant", avatar="🌸"):
            with st.spinner("🌸 Hana lagi mikir..."):
                _resp = chat_response(_user_msg, st.session_state["hana_history"])

            _text = _resp.get("text", "")
            st.markdown(_text)

        # Simpan AI response
        st.session_state["hana_history"].append({"role": "assistant", "content": _text})

        # Kalau intent UPDATE atau DELETE, set pending
        if _resp.get("parsed"):
            st.session_state["hana_pending_update"] = _resp["parsed"]

        st.rerun()

    # === CLEAR ===
    if st.session_state["hana_history"]:
        st.markdown("---")
        _col_clr, _ = st.columns([1, 4])
        with _col_clr:
            if st.button("🗑️ Clear Chat", key="btn_clear_hana", width="stretch"):
                st.session_state["hana_history"] = []
                st.session_state["hana_pending_update"] = None
                st.rerun()


# =========================================================================
# TAB 2: SCREENSHOT (OCR)
# =========================================================================
def render_screenshot():
    st.markdown("### 📸 Upload Screenshot Kalender Shift")
    st.caption("💡 Upload screenshot dari web absen → AI baca kode shift otomatis")

    try:
        from modules.ocr_handler import (
            log_ocr_upload,
        )
        _ocr_available = True
    except ImportError:
        _ocr_available = False

    if not _ocr_available:
        st.info("💡 Fitur OCR butuh file `modules/ocr_handler.py`. Belum siap.")
        return

    try:
        from modules.ocr_ai_handler import ocr_ai_smart
        from modules.ocr_handler import save_ocr_to_master_shift
    except ImportError as _e:
        st.error(f"❌ Import OCR error: {_e}")
        return

    # Pilih personil & bulan
    _personil_df = load_personil_master(only_active=True)
    _personil_list = _personil_df["nama"].tolist() if not _personil_df.empty else []

    col_n1, col_n2, col_n3 = st.columns([2, 1, 1])
    with col_n1:
        _nama_pilih = st.selectbox("👤 Nama Personil", options=_personil_list, key="ocr_nama") if _personil_list else None
    with col_n2:
        _bulan_ocr = st.selectbox(
            "📅 Bulan",
            options=list(NAMA_BULAN_ID.keys()),
            format_func=lambda x: NAMA_BULAN_ID[x],
            index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
            key="ocr_bulan",
        )
    with col_n3:
        _tahun_ocr = st.number_input(
            "📆 Tahun", min_value=2024, max_value=2100,
            value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
            key="ocr_tahun",
        )

    st.markdown("---")

    _uploaded = st.file_uploader(
        "Upload screenshot kalender (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        key="ocr_upload",
    )

    if _uploaded and _nama_pilih:
        st.image(_uploaded, caption=f"Preview: {_uploaded.name}", width="stretch")

        if st.button("🔍 PROSES OCR", type="primary", width="stretch", key="btn_ocr"):
            with st.spinner("🌸 Hana lagi baca kalender... (10-20 detik)"):
                _ai_result = ocr_ai_smart(
                    _uploaded.getvalue(),
                    nama_personil=_nama_pilih,
                    bulan=_bulan_ocr,
                    tahun=_tahun_ocr,
                )

            if _ai_result["success"]:
                _shift_map = _ai_result["shift_map"]
                _tanggal_list = []
                for _tgl_str, _kode in sorted(_shift_map.items()):
                    _tanggal_list.append({
                        "tanggal_int": int(_tgl_str.split("-")[2]),
                        "kode": _kode,
                    })

                st.session_state["ocr_result"] = {
                    "shift_map": _shift_map,
                    "tanggal_list": _tanggal_list,
                    "nama": _nama_pilih,
                    "bulan": _bulan_ocr,
                    "tahun": _tahun_ocr,
                    "provider": _ai_result.get("provider", "?"),
                }
                st.rerun()
            else:
                st.error(f"❌ OCR gagal: {_ai_result.get('error')}")

    # Preview hasil OCR
    if st.session_state.get("ocr_result"):
        _res = st.session_state["ocr_result"]
        _shift_map = _res["shift_map"]

        st.markdown("---")
        st.markdown("#### 📊 Hasil OCR")
        st.write(f"**Nama:** {_res['nama']} • **Provider:** {_res['provider']}")

        _preview_rows = []
        for _tgl_str, _kode in sorted(_shift_map.items()):
            _tgl = pd.to_datetime(_tgl_str)
            _info = KODE_SHIFT.get(_kode, {"label": "-", "icon": "❓"})
            _preview_rows.append({
                "📅 Tanggal": _tgl.strftime("%d/%m/%Y"),
                "🎨 Kode": _kode,
                "📋 Ket.": _info["label"],
            })
        st.dataframe(pd.DataFrame(_preview_rows), width="stretch", hide_index=True)

        _col1, _col2 = st.columns(2)
        with _col1:
            if st.button("💾 SIMPAN KE MASTER SHIFT", type="primary", width="stretch", key="btn_ocr_save"):
                with st.spinner("⏳ Menyimpan..."):
                    _ok, _msg = save_ocr_to_master_shift(
                        nama=_res["nama"],
                        bulan=_res["bulan"],
                        tahun=_res["tahun"],
                        shift_map=_shift_map,
                        sumber="ocr",
                    )
                if _ok:
                    st.success(_msg)
                    st.balloons()
                    st.session_state["ocr_result"] = None
                    st.cache_data.clear()
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.error(_msg)

        with _col2:
            if st.button("❌ BATAL", width="stretch", key="btn_ocr_cancel"):
                st.session_state["ocr_result"] = None
                st.rerun()
# =========================================================================
# TAB 3: MATRIX (SUB-TAB)
# =========================================================================
def render_matrix():
    st.markdown("### 📊 Matrix & Data")

    if "matrix_sub" not in st.session_state:
        st.session_state["matrix_sub"] = "tabel"

    _subs = [
        ("tabel", "📋 Tabel Master"),
        ("personil", "👥 Personil Aktif"),
        ("download", "📥 Download"),
    ]

    _sub_cols = st.columns(len(_subs))  # ✅ Rename biar gak bentrok
    for _i, (_key, _label) in enumerate(_subs):
        with _sub_cols[_i]:
            _is_active = st.session_state["matrix_sub"] == _key
            if st.button(
                _label,
                key=f"matrix_sub_{_key}",
                width="stretch",
                type="primary" if _is_active else "secondary",
            ):
                st.session_state["matrix_sub"] = _key
                st.rerun()

    st.markdown("---")

    # === SUB: TABEL MASTER ===
    if st.session_state["matrix_sub"] == "tabel":
        _col_b1, _col_b2, _col_b3 = st.columns([2, 1, 1])
        with _col_b1:
            _bulan_pilih = st.selectbox(
                "📅 Bulan",
                options=list(NAMA_BULAN_ID.keys()),
                format_func=lambda x: NAMA_BULAN_ID[x],
                index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
                key="matrix_bulan",
            )
        with _col_b2:
            _tahun_pilih = st.number_input(
                "📆 Tahun", min_value=2024, max_value=2100,
                value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
                key="matrix_tahun",
            )
        with _col_b3:
            if st.button("🔄 Refresh", width="stretch", key="matrix_refresh"):
                st.cache_data.clear()
                st.rerun()

        with st.spinner("⏳ Load matrix..."):
            _matrix_df = load_master_shift_matrix(_bulan_pilih, _tahun_pilih)

        if _matrix_df.empty:
            st.info("📭 Belum ada data shift bulan ini.")
        else:
            _all_cols = list(_matrix_df.columns)
            _nama_col = "NAMA"
            _cols_1_15 = [_nama_col] + [c for c in _all_cols if c != _nama_col and str(c).isdigit() and 1 <= int(c) <= 15]
            _cols_16_31 = [_nama_col] + [c for c in _all_cols if c != _nama_col and str(c).isdigit() and 16 <= int(c) <= 31]

            st.markdown("#### 📅 Tanggal 1 - 15")
            if len(_cols_1_15) > 1:
                st.dataframe(
                    _matrix_df[_cols_1_15],
                    width="stretch",
                    hide_index=True,
                    height=min(500, 40 + len(_matrix_df) * 38),
                )

            st.markdown("#### 📅 Tanggal 16 - 31")
            if len(_cols_16_31) > 1:
                st.dataframe(
                    _matrix_df[_cols_16_31],
                    width="stretch",
                    hide_index=True,
                    height=min(500, 40 + len(_matrix_df) * 38),
                )

    # === SUB: PERSONIL ===
    elif st.session_state["matrix_sub"] == "personil":
        _personil_all = load_personil_master(only_active=False)
        _personil_aktif = load_personil_master(only_active=True)

        _c1, _c2 = st.columns(2)
        with _c1:
            st.metric("👥 Personil Aktif", len(_personil_aktif))
        with _c2:
            st.metric("👤 Total", len(_personil_all))

        st.markdown("---")

        with st.expander("➕ Tambah Personil Baru"):
            with st.form("form_add_personil"):
                _new_nama = st.text_input("Nama", placeholder="Contoh: BUDI").strip().upper()
                _btn_add = st.form_submit_button("💾 TAMBAH", width="stretch", type="primary")
                if _btn_add:
                    if not _new_nama:
                        st.error("⚠️ Nama wajib diisi!")
                    else:
                        _ok, _msg = add_personil(_new_nama)
                        if _ok:
                            st.success(_msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(_msg)

        st.markdown("#### 📋 Daftar Personil")
        if _personil_all.empty:
            st.info("📭 Belum ada personil.")
        else:
            for _, _row in _personil_all.sort_values("urutan").iterrows():
                _nama = _row["nama"]
                _aktif = _row["aktif"]
                _col_l1, _col_l2 = st.columns([3, 1])
                with _col_l1:
                    _icon = "✅" if _aktif else "❌"
                    _status = "AKTIF" if _aktif else "NON-AKTIF"
                    st.markdown(f"{_icon} **{_nama}** — {_status}")
                with _col_l2:
                    if _aktif:
                        if st.button("🚫 Non-aktif", key=f"deact_{_nama}", width="stretch"):
                            update_personil_status(_nama, False)
                            st.rerun()
                    else:
                        if st.button("✅ Aktifkan", key=f"act_{_nama}", width="stretch"):
                            update_personil_status(_nama, True)
                            st.rerun()

    # === SUB: DOWNLOAD ===
    elif st.session_state["matrix_sub"] == "download":
        _col_d1, _col_d2 = st.columns(2)
        with _col_d1:
            _dl_bulan = st.selectbox(
                "📅 Bulan",
                options=list(NAMA_BULAN_ID.keys()),
                format_func=lambda x: NAMA_BULAN_ID[x],
                index=datetime.now(ZoneInfo("Asia/Jakarta")).month - 1,
                key="dl_bulan",
            )
        with _col_d2:
            _dl_tahun = st.number_input(
                "📆 Tahun", min_value=2024, max_value=2100,
                value=datetime.now(ZoneInfo("Asia/Jakarta")).year,
                key="dl_tahun",
            )

        with st.spinner("⏳ Prepare Excel..."):
            _dl_matrix = load_master_shift_matrix(_dl_bulan, _dl_tahun)

        if _dl_matrix.empty:
            st.warning("📭 Belum ada data.")
        else:
            _excel_bytes = generate_master_shift_excel(_dl_matrix, _dl_bulan, _dl_tahun)
            if _excel_bytes:
                st.download_button(
                    label="📥 DOWNLOAD EXCEL",
                    data=_excel_bytes,
                    file_name=f"Master_Shift_{NAMA_BULAN_ID[_dl_bulan]}_{_dl_tahun}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    type="primary",
                    key="dl_excel",
                )


# =========================================================================
# TAB 4: USAGE
# =========================================================================
def render_usage():
    from modules.token_monitor import render_usage_dashboard
    st.markdown("### 📈 Penggunaan AI")
    st.caption("Pantau token & quota per AI.")
    render_usage_dashboard()


# =========================================================================
# ROUTING TAB
# =========================================================================
_tab = st.session_state["ms_tab"]

if _tab == "hana":
    render_hana()
elif _tab == "screenshot":
    render_screenshot()
elif _tab == "matrix":
    render_matrix()
elif _tab == "usage":
    render_usage()


# =========================================================================
# FOOTER
# =========================================================================
st.markdown(
    "<div class='copyright-footer'>🌸 Dashboard SO KGS V.2 — Hana Edition 🌸</div>",
    unsafe_allow_html=True,
)