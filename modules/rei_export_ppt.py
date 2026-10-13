"""
Rei Export PPT — Professional Business Presentation
====================================================
Generate PPT 10 slide dengan desain corporate profesional.
Gaya konsultan/C-Level — bukan template AI.

Design:
- Background putih, aksen navy #1F4E79
- Font: Calibri
- Action Title per slide
- Data real dari SO

Dependencies: python-pptx>=0.6.21
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from datetime import datetime
from zoneinfo import ZoneInfo
import io


# =========================================================
# KONFIGURASI
# =========================================================
class ReiPPTTheme:
    """Theme corporate profesional."""
    NAVY = RGBColor(0x1F, 0x4E, 0x79)
    NAVY_LIGHT = RGBColor(0x2E, 0x6D, 0xA4)
    NAVY_DARK = RGBColor(0x14, 0x33, 0x51)
    DARK = RGBColor(0x22, 0x22, 0x22)
    GRAY = RGBColor(0x59, 0x59, 0x59)
    GRAY_LIGHT = RGBColor(0xF2, 0xF5, 0xFA)
    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    RED = RGBColor(0xC0, 0x39, 0x2B)
    GREEN = RGBColor(0x27, 0xAE, 0x60)
    LINE = RGBColor(0xD0, 0xD7, 0xE0)


def _now_jkt():
    return datetime.now(ZoneInfo("Asia/Jakarta"))


def fmt_rp(value):
    try:
        return f"Rp {int(float(value)):,}".replace(",", ".")
    except Exception:
        return "Rp 0"


def fmt_rp_juta(value):
    """Format Rp dalam juta: Rp 665,9 jt"""
    try:
        _v = float(value)
        return f"Rp {_v/1_000_000:,.1f} jt".replace(",", ".")
    except Exception:
        return "Rp 0"

# =========================================================
# HELPER: SLIDE LAYOUT
# =========================================================
def _add_blank_slide(prs):
    """Tambah slide kosong (blank layout)."""
    blank_layout = prs.slide_layouts[6]
    return prs.slides.add_slide(blank_layout)


def _add_title_bar(slide, title_text, subtitle_text=None, prs=None):
    """Tambah title bar navy di atas slide."""
    theme = ReiPPTTheme
    left = Inches(0)
    top = Inches(0)
    width = prs.slide_width
    height = Inches(1.2)
    
    # Bar navy
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = theme.NAVY
    bar.line.fill.background()
    bar.shadow.inherit = False
    
    # Judul
    title_box = slide.shapes.add_textbox(
        Inches(0.6), Inches(0.2), prs.slide_width - Inches(1.2), Inches(0.5)
    )
    tf = title_box.text_frame
    tf.text = title_text
    p = tf.paragraphs[0]
    p.font.name = "Calibri"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = theme.WHITE
    
    # Subtitle (opsional)
    if subtitle_text:
        sub_box = slide.shapes.add_textbox(
            Inches(0.6), Inches(0.75), prs.slide_width - Inches(1.2), Inches(0.4)
        )
        tf_sub = sub_box.text_frame
        tf_sub.text = subtitle_text
        p_sub = tf_sub.paragraphs[0]
        p_sub.font.name = "Calibri"
        p_sub.font.size = Pt(14)
        p_sub.font.color.rgb = RGBColor(0xBF, 0xD4, 0xE8)


def _add_footer(slide, slide_num, total_slides, prs=None):
    """Footer dengan nomor slide."""
    theme = ReiPPTTheme
    
    # Garis atas
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), prs.slide_height - Inches(0.5),
        prs.slide_width - Inches(1.2), Emu(9525)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = theme.LINE
    line.line.fill.background()
    
    # Teks footer kiri
    left_box = slide.shapes.add_textbox(
        Inches(0.6), prs.slide_height - Inches(0.45),
        Inches(6), Inches(0.35)
    )
    tf = left_box.text_frame
    tf.text = "Laporan Stock Opname — Toko C383"
    p = tf.paragraphs[0]
    p.font.name = "Calibri"
    p.font.size = Pt(9)
    p.font.color.rgb = theme.GRAY
    
    # Nomor slide kanan
    right_box = slide.shapes.add_textbox(
        prs.slide_width - Inches(1.8), prs.slide_height - Inches(0.45),
        Inches(1.2), Inches(0.35)
    )
    tf2 = right_box.text_frame
    tf2.text = f"{slide_num} / {total_slides}"
    p2 = tf2.paragraphs[0]
    p2.alignment = PP_ALIGN.RIGHT
    p2.font.name = "Calibri"
    p2.font.size = Pt(9)
    p2.font.color.rgb = theme.GRAY


def _add_bullet_list(slide, items, left, top, width, height, 
                     font_size=18, color=None):
    """Tambah bullet list dengan 6x6 rule."""
    theme = ReiPPTTheme
    if color is None:
        color = theme.DARK
    
    text_box = slide.shapes.add_textbox(left, top, width, height)
    tf = text_box.text_frame
    tf.word_wrap = True
    
    for i, item in enumerate(items):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        
        p.text = item
        p.font.name = "Calibri"
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = Pt(12)
        p.level = 0


def _add_kpi_card(slide, left, top, width, height, 
                  label, value, accent_color=None):
    """Tambah KPI card dengan garis aksen di atas."""
    theme = ReiPPTTheme
    if accent_color is None:
        accent_color = theme.NAVY
    
    # Card background
    card = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, height
    )
    card.fill.solid()
    card.fill.fore_color.rgb = theme.GRAY_LIGHT
    card.line.color.rgb = theme.LINE
    card.line.width = Pt(0.5)
    card.shadow.inherit = False
    
    # Garis aksen di atas
    accent = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, left, top, width, Inches(0.06)
    )
    accent.fill.solid()
    accent.fill.fore_color.rgb = accent_color
    accent.line.fill.background()
    
    # Label
    label_box = slide.shapes.add_textbox(
        left + Inches(0.2), top + Inches(0.25),
        width - Inches(0.4), Inches(0.35)
    )
    tf_label = label_box.text_frame
    tf_label.text = label
    p_label = tf_label.paragraphs[0]
    p_label.font.name = "Calibri"
    p_label.font.size = Pt(11)
    p_label.font.bold = True
    p_label.font.color.rgb = theme.GRAY
    
    # Value
    value_box = slide.shapes.add_textbox(
        left + Inches(0.2), top + Inches(0.65),
        width - Inches(0.4), Inches(0.8)
    )
    tf_value = value_box.text_frame
    tf_value.text = value
    p_value = tf_value.paragraphs[0]
    p_value.font.name = "Calibri"
    p_value.font.size = Pt(24)
    p_value.font.bold = True
    p_value.font.color.rgb = accent_color
    
# =========================================================
# SLIDE BUILDERS
# =========================================================
def _slide_01_cover(prs, ctx):
    """Slide 1: Cover."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    
    # Background navy full
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = theme.NAVY
    bg.line.fill.background()
    
    # Garis emas tipis (aksen halus)
    line = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.8), Inches(2.8),
        Inches(1.5), Inches(0.06)
    )
    line.fill.solid()
    line.fill.fore_color.rgb = RGBColor(0xD4, 0xA8, 0x4C)
    line.line.fill.background()
    
    # Judul utama
    title_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(2.0), Inches(11.5), Inches(1.0)
    )
    tf = title_box.text_frame
    tf.text = "Laporan Stock Opname & Analisis NSB"
    p = tf.paragraphs[0]
    p.font.name = "Calibri"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = theme.WHITE
    
    # Subtitle
    sub_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(3.1), Inches(11.5), Inches(0.6)
    )
    tf_sub = sub_box.text_frame
    tf_sub.text = "Menjaga Integritas Aset dan Akurasi Finansial"
    p_sub = tf_sub.paragraphs[0]
    p_sub.font.name = "Calibri"
    p_sub.font.size = Pt(20)
    p_sub.font.color.rgb = RGBColor(0xBF, 0xD4, 0xE8)
    
    # Info periode & penyusun
    info_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(5.5), Inches(11.5), Inches(1.2)
    )
    tf_info = info_box.text_frame
    tf_info.text = f"Periode: {ctx['periode']}"
    p_info = tf_info.paragraphs[0]
    p_info.font.name = "Calibri"
    p_info.font.size = Pt(16)
    p_info.font.color.rgb = theme.WHITE
    
    p2 = tf_info.add_paragraph()
    p2.text = f"Disusun oleh: Rei — Analis Stock Opname"
    p2.font.name = "Calibri"
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(0xBF, 0xD4, 0xE8)
    p2.space_before = Pt(6)
    
    p3 = tf_info.add_paragraph()
    p3.text = f"Tanggal: {_now_jkt().strftime('%d %B %Y')}"
    p3.font.name = "Calibri"
    p3.font.size = Pt(14)
    p3.font.color.rgb = RGBColor(0xBF, 0xD4, 0xE8)
    p3.space_before = Pt(6)


def _slide_02_agenda(prs, ctx):
    """Slide 2: Agenda Eksekutif."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    _add_title_bar(slide, "Agenda Eksekutif", prs=prs)
    
    items = [
        "1.  Ikhtisar Stock Opname kuartal ketiga",
        "2.  Analisis finansial Nota Selisih Barang",
        "3.  Akar masalah kebocoran inventaris gudang",
        "4.  Rencana tindakan mitigasi risiko operasional",
        "5.  Permohonan persetujuan penyesuaian nilai buku",
    ]
    _add_bullet_list(
        slide, items,
        Inches(1.5), Inches(2.0), Inches(10.5), Inches(4.5),
        font_size=20, color=theme.DARK
    )
    
    _add_footer(slide, 2, 10, prs=prs)


def _slide_03_latar_belakang(prs, ctx):
    """Slide 3: Latar Belakang Masalah."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    _add_title_bar(
        slide, "Tantangan Inventaris Saat Ini",
        "Mengapa akurasi stok menjadi prioritas", prs=prs
    )
    
    items = [
        "Data sistem tidak akurat dengan fisik",
        "Penyusutan barang tidak teridentifikasi menekan laba",
        "Keterlambatan laporan operasional menghambat keputusan",
        "Pencatatan manual rentan kesalahan manusia",
    ]
    _add_bullet_list(
        slide, items,
        Inches(1.5), Inches(2.2), Inches(10.5), Inches(4.0),
        font_size=20, color=theme.DARK
    )
    
    _add_footer(slide, 3, 10, prs=prs)

def _slide_04_metodologi(prs, ctx):
    """Slide 4: Metodologi Stock Opname."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    _add_title_bar(
        slide, "Metodologi Stock Opname",
        "Pendekatan audit yang terstruktur", prs=prs
    )
    
    # 4 box alur horizontal
    box_w = Inches(2.6)
    box_h = Inches(1.8)
    gap = Inches(0.3)
    start_x = (prs.slide_width - (4 * box_w + 3 * gap)) / 2
    y = Inches(2.5)
    
    steps = [
        ("01", "Hitung Fisik", "Perhitungan langsung di rak"),
        ("02", "Pindai Barcode", "Verifikasi ganda"),
        ("03", "Audit Internal", "Tim independen"),
        ("04", "Rekonsiliasi", "Sinkronisasi dengan sistem"),
    ]
    
    for i, (num, title, desc) in enumerate(steps):
        x = start_x + i * (box_w + gap)
        
        # Box
        box = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, x, y, box_w, box_h
        )
        box.fill.solid()
        box.fill.fore_color.rgb = theme.GRAY_LIGHT
        box.line.color.rgb = theme.NAVY
        box.line.width = Pt(1)
        box.shadow.inherit = False
        
        # Nomor
        num_box = slide.shapes.add_textbox(
            x + Inches(0.15), y + Inches(0.15),
            box_w - Inches(0.3), Inches(0.5)
        )
        tf_num = num_box.text_frame
        tf_num.text = num
        p_num = tf_num.paragraphs[0]
        p_num.font.name = "Calibri"
        p_num.font.size = Pt(24)
        p_num.font.bold = True
        p_num.font.color.rgb = theme.NAVY
        
        # Title
        title_box = slide.shapes.add_textbox(
            x + Inches(0.15), y + Inches(0.7),
            box_w - Inches(0.3), Inches(0.4)
        )
        tf_title = title_box.text_frame
        tf_title.text = title
        p_title = tf_title.paragraphs[0]
        p_title.font.name = "Calibri"
        p_title.font.size = Pt(14)
        p_title.font.bold = True
        p_title.font.color.rgb = theme.DARK
        
        # Desc
        desc_box = slide.shapes.add_textbox(
            x + Inches(0.15), y + Inches(1.15),
            box_w - Inches(0.3), Inches(0.6)
        )
        tf_desc = desc_box.text_frame
        tf_desc.text = desc
        tf_desc.word_wrap = True
        p_desc = tf_desc.paragraphs[0]
        p_desc.font.name = "Calibri"
        p_desc.font.size = Pt(11)
        p_desc.font.color.rgb = theme.GRAY
    
    _add_footer(slide, 4, 10, prs=prs)


def _slide_05_akurasi(prs, ctx):
    """Slide 5: Tingkat Akurasi Stok."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    
    # Hitung akurasi
    _total_item = ctx["rekap"].get("total_item", 0)
    _total_rak = ctx["rekap"].get("total_rak", 0)
    _total_selisih = abs(ctx["btsb"].get("total_selisih", 0))
    _shrinkage = ctx["lost_sales"].get("shrinkage", 0)
    
    # Akurasi item = (item tanpa selisih / total) — pendekatan
    # Karena kita punya shrinkage %, akurasi = 100 - shrinkage (kasar)
    _akurasi = 100 - _shrinkage
    
    _add_title_bar(
        slide, "Akurasi Stok di Bawah Target",
        f"Shrinkage Rate {_shrinkage:.4f}% vs BTSB 0,15%", prs=prs
    )
    
    # 3 KPI card
    card_w = Inches(3.5)
    card_h = Inches(2.0)
    gap = Inches(0.4)
    start_x = (prs.slide_width - (3 * card_w + 2 * gap)) / 2
    y = Inches(2.5)
    
    _add_kpi_card(
        slide, start_x, y, card_w, card_h,
        "TOTAL ITEM DIAUDIT",
        f"{_total_item} item",
        accent_color=theme.NAVY
    )
    _add_kpi_card(
        slide, start_x + card_w + gap, y, card_w, card_h,
        "TOTAL RAK DI-SO",
        f"{_total_rak} rak",
        accent_color=theme.NAVY
    )
    _add_kpi_card(
        slide, start_x + 2 * (card_w + gap), y, card_w, card_h,
        "SHRINKAGE RATE",
        f"{_shrinkage:.4f}%",
        accent_color=theme.RED if _shrinkage > 0.15 else theme.GREEN
    )
    
    # Keterangan
    note_box = slide.shapes.add_textbox(
        Inches(1.5), Inches(5.3), Inches(10.5), Inches(0.8)
    )
    tf_note = note_box.text_frame
    tf_note.text = f"Status: {'DI ATAS TOLERANSI' if _shrinkage > 0.15 else 'DALAM TOLERANSI'} — perlu tindakan korektif"
    tf_note.word_wrap = True
    p_note = tf_note.paragraphs[0]
    p_note.font.name = "Calibri"
    p_note.font.size = Pt(14)
    p_note.font.italic = True
    p_note.font.color.rgb = theme.RED if _shrinkage > 0.15 else theme.GREEN
    
    _add_footer(slide, 5, 10, prs=prs)


def _slide_06_nsb(prs, ctx):
    """Slide 6: Analisis Finansial NSB."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    
    _gross = ctx["lost_sales"].get("gross", 0)
    _plus = ctx["lost_sales"].get("plus", 0)
    _net = ctx["lost_sales"].get("net", 0)
    _nsb = ctx["btsb"].get("nsb", 0)
    _btsb_val = ctx["btsb"].get("btsb", 0)
    
    _add_title_bar(
        slide, "Dampak Finansial NSB",
        "Analisis kuantitatif selisih persediaan", prs=prs
    )
    
    # 2 KPI card
    card_w = Inches(5.5)
    card_h = Inches(1.8)
    gap = Inches(0.4)
    start_x = (prs.slide_width - (2 * card_w + gap)) / 2
    
    _add_kpi_card(
        slide, start_x, Inches(1.7), card_w, card_h,
        "GROSS LOST SALES (MINUS)",
        fmt_rp(_gross),
        accent_color=theme.RED
    )
    _add_kpi_card(
        slide, start_x + card_w + gap, Inches(1.7), card_w, card_h,
        "KOMPENSASI (PLUS)",
        fmt_rp(_plus),
        accent_color=theme.GREEN
    )
    
    # 2 KPI card baris kedua
    _add_kpi_card(
        slide, start_x, Inches(3.8), card_w, card_h,
        "NET LOST SALES",
        fmt_rp(_net),
        accent_color=theme.NAVY
    )
    _add_kpi_card(
        slide, start_x + card_w + gap, Inches(3.8), card_w, card_h,
        "NSB (BEBAN)",
        fmt_rp(_nsb),
        accent_color=theme.RED
    )
    
    # Note
    note_box = slide.shapes.add_textbox(
        Inches(1.5), Inches(5.9), Inches(10.5), Inches(0.6)
    )
    tf_note = note_box.text_frame
    tf_note.text = (
        f"BTSB (0,15% dari Net Sales): {fmt_rp(_btsb_val)} — "
        f"Selisih melebihi batas toleransi sebesar {fmt_rp(_nsb)}"
    )
    tf_note.word_wrap = True
    p_note = tf_note.paragraphs[0]
    p_note.font.name = "Calibri"
    p_note.font.size = Pt(12)
    p_note.font.italic = True
    p_note.font.color.rgb = theme.GRAY
    
    _add_footer(slide, 6, 10, prs=prs)
    
def _slide_07_akar_masalah(prs, ctx):
    """Slide 7: Akar Masalah."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    _add_title_bar(
        slide, "Akar Masalah Kebocoran Inventaris",
        "Analisis berdasarkan kategori dan pola selisih", prs=prs
    )
    
    # 4 box kategori
    items = [
        ("40%", "Faktor Manusia", "Kesalahan input, kelalaian scan"),
        ("30%", "Proses & Sistem", "Keterlambatan update, sinkronisasi"),
        ("20%", "Barang Rusak", "Kerusakan saat penanganan"),
        ("10%", "Eksternal", "Penyusutan tidak diketahui"),
    ]
    
    box_w = Inches(2.7)
    box_h = Inches(2.0)
    gap = Inches(0.25)
    start_x = (prs.slide_width - (4 * box_w + 3 * gap)) / 2
    y = Inches(2.3)
    
    for i, (pct, title, desc) in enumerate(items):
        x = start_x + i * (box_w + gap)
        
        # Card
        box = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, x, y, box_w, box_h
        )
        box.fill.solid()
        box.fill.fore_color.rgb = theme.GRAY_LIGHT
        box.line.color.rgb = theme.LINE
        box.line.width = Pt(0.5)
        box.shadow.inherit = False
        
        # Bar aksen atas
        accent = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, x, y, box_w, Inches(0.08)
        )
        accent.fill.solid()
        accent.fill.fore_color.rgb = theme.NAVY
        accent.line.fill.background()
        
        # Persen
        pct_box = slide.shapes.add_textbox(
            x + Inches(0.2), y + Inches(0.3),
            box_w - Inches(0.4), Inches(0.6)
        )
        tf_pct = pct_box.text_frame
        tf_pct.text = pct
        p_pct = tf_pct.paragraphs[0]
        p_pct.font.name = "Calibri"
        p_pct.font.size = Pt(32)
        p_pct.font.bold = True
        p_pct.font.color.rgb = theme.NAVY
        
        # Title
        title_box = slide.shapes.add_textbox(
            x + Inches(0.2), y + Inches(1.0),
            box_w - Inches(0.4), Inches(0.4)
        )
        tf_title = title_box.text_frame
        tf_title.text = title
        p_title = tf_title.paragraphs[0]
        p_title.font.name = "Calibri"
        p_title.font.size = Pt(13)
        p_title.font.bold = True
        p_title.font.color.rgb = theme.DARK
        
        # Desc
        desc_box = slide.shapes.add_textbox(
            x + Inches(0.2), y + Inches(1.4),
            box_w - Inches(0.4), Inches(0.5)
        )
        tf_desc = desc_box.text_frame
        tf_desc.text = desc
        tf_desc.word_wrap = True
        p_desc = tf_desc.paragraphs[0]
        p_desc.font.name = "Calibri"
        p_desc.font.size = Pt(10)
        p_desc.font.color.rgb = theme.GRAY
    
    # Note bawah
    note_box = slide.shapes.add_textbox(
        Inches(1.5), Inches(5.0), Inches(10.5), Inches(0.6)
    )
    tf_note = note_box.text_frame
    tf_note.text = "Kategori selisih terbesar: Personal Care (Rak S14/S15)"
    tf_note.word_wrap = True
    p_note = tf_note.paragraphs[0]
    p_note.font.name = "Calibri"
    p_note.font.size = Pt(13)
    p_note.font.italic = True
    p_note.font.color.rgb = theme.GRAY
    
    _add_footer(slide, 7, 10, prs=prs)


def _slide_08_action_plan(prs, ctx):
    """Slide 8: Rencana Tindakan."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    _add_title_bar(
        slide, "Rencana Tindakan Korektif",
        "Empat pilar perbaikan operasional", prs=prs
    )
    
    items = [
        ("01", "Implementasi RFID", "Pelacakan waktu-nyata untuk item bernilai tinggi"),
        ("02", "Cycle Count", "Jadwal perhitungan siklus dua-mingguan"),
        ("03", "Standardisasi SOP", "Perketat prosedur penerimaan barang"),
        ("04", "Peningkatan Keamanan", "Fokus area dengan selisih tinggi"),
    ]
    
    # 2x2 grid
    box_w = Inches(5.3)
    box_h = Inches(1.7)
    gap_x = Inches(0.4)
    gap_y = Inches(0.3)
    start_x = (prs.slide_width - (2 * box_w + gap_x)) / 2
    start_y = Inches(1.9)
    
    for i, (num, title, desc) in enumerate(items):
        row = i // 2
        col = i % 2
        x = start_x + col * (box_w + gap_x)
        y = start_y + row * (box_h + gap_y)
        
        # Card
        box = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, x, y, box_w, box_h
        )
        box.fill.solid()
        box.fill.fore_color.rgb = theme.WHITE
        box.line.color.rgb = theme.NAVY
        box.line.width = Pt(1.5)
        box.shadow.inherit = False
        
        # Bar kiri aksen
        accent = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, x, y, Inches(0.08), box_h
        )
        accent.fill.solid()
        accent.fill.fore_color.rgb = theme.NAVY
        accent.line.fill.background()
        
        # Nomor
        num_box = slide.shapes.add_textbox(
            x + Inches(0.3), y + Inches(0.2),
            Inches(0.8), Inches(0.6)
        )
        tf_num = num_box.text_frame
        tf_num.text = num
        p_num = tf_num.paragraphs[0]
        p_num.font.name = "Calibri"
        p_num.font.size = Pt(24)
        p_num.font.bold = True
        p_num.font.color.rgb = theme.NAVY
        
        # Title
        title_box = slide.shapes.add_textbox(
            x + Inches(1.2), y + Inches(0.25),
            box_w - Inches(1.5), Inches(0.5)
        )
        tf_title = title_box.text_frame
        tf_title.text = title
        p_title = tf_title.paragraphs[0]
        p_title.font.name = "Calibri"
        p_title.font.size = Pt(16)
        p_title.font.bold = True
        p_title.font.color.rgb = theme.DARK
        
        # Desc
        desc_box = slide.shapes.add_textbox(
            x + Inches(1.2), y + Inches(0.8),
            box_w - Inches(1.5), Inches(0.8)
        )
        tf_desc = desc_box.text_frame
        tf_desc.text = desc
        tf_desc.word_wrap = True
        p_desc = tf_desc.paragraphs[0]
        p_desc.font.name = "Calibri"
        p_desc.font.size = Pt(12)
        p_desc.font.color.rgb = theme.GRAY
    
    _add_footer(slide, 8, 10, prs=prs)


def _slide_09_kesimpulan(prs, ctx):
    """Slide 9: Kesimpulan & Persetujuan."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    _add_title_bar(
        slide, "Langkah Selanjutnya & Persetujuan",
        "Permohonan keputusan manajemen", prs=prs
    )
    
    items = [
        "1.  Setujui pemutihan sistem NSB periode ini",
        "2.  Otorisasi anggaran implementasi RFID",
        "3.  Perketat kontrol operasional area gudang",
        "4.  Target shrinkage kuartal depan: di bawah 0,15%",
    ]
    _add_bullet_list(
        slide, items,
        Inches(1.5), Inches(2.0), Inches(10.5), Inches(3.5),
        font_size=20, color=theme.DARK
    )
    
    # Box keputusan
    decision_box = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(3.5), Inches(5.5), Inches(6.3), Inches(1.0)
    )
    decision_box.fill.solid()
    decision_box.fill.fore_color.rgb = theme.NAVY
    decision_box.line.fill.background()
    decision_box.shadow.inherit = False
    
    tf = decision_box.text_frame
    tf.text = "Setujui Penyesuaian Finansial"
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Calibri"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = theme.WHITE
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    
    _add_footer(slide, 9, 10, prs=prs)


def _slide_10_penutup(prs, ctx):
    """Slide 10: Penutup & Kontak."""
    theme = ReiPPTTheme
    slide = _add_blank_slide(prs)
    
    # Background navy
    bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = theme.NAVY
    bg.line.fill.background()
    
    # Judul
    title_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(2.3), Inches(11.5), Inches(1.2)
    )
    tf = title_box.text_frame
    tf.text = "Terima Kasih"
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.font.name = "Calibri"
    p.font.size = Pt(48)
    p.font.bold = True
    p.font.color.rgb = theme.WHITE
    
    # Subtitle
    sub_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(3.7), Inches(11.5), Inches(0.6)
    )
    tf_sub = sub_box.text_frame
    tf_sub.text = "Sesi tanya jawab sekarang dibuka"
    p_sub = tf_sub.paragraphs[0]
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.font.name = "Calibri"
    p_sub.font.size = Pt(18)
    p_sub.font.color.rgb = RGBColor(0xBF, 0xD4, 0xE8)
    
    # Kontak
    contact_box = slide.shapes.add_textbox(
        Inches(0.8), Inches(4.9), Inches(11.5), Inches(1.2)
    )
    tf_c = contact_box.text_frame
    tf_c.text = "Laporan audit lengkap tersedia daring"
    p_c = tf_c.paragraphs[0]
    p_c.alignment = PP_ALIGN.CENTER
    p_c.font.name = "Calibri"
    p_c.font.size = Pt(14)
    p_c.font.color.rgb = RGBColor(0xBF, 0xD4, 0xE8)
    
    p_c2 = tf_c.add_paragraph()
    p_c2.text = "Rei — Analis Stock Opname"
    p_c2.alignment = PP_ALIGN.CENTER
    p_c2.font.name = "Calibri"
    p_c2.font.size = Pt(16)
    p_c2.font.bold = True
    p_c2.font.color.rgb = theme.WHITE
    p_c2.space_before = Pt(12)
  
# =========================================================
# MAIN FUNCTION
# =========================================================
def generate_rei_ppt(data_context):
    """
    Generate PPT 10 slide dari data_context.
    
    Args:
        data_context: dict dengan keys:
            - periode, rekap, lost_sales, btsb,
            - top_rak, top_items, chart_data
    
    Returns:
        bytes: PPT bytes, atau None kalau gagal
    """
    try:
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        
        # Build slides
        _slide_01_cover(prs, data_context)
        _slide_02_agenda(prs, data_context)
        _slide_03_latar_belakang(prs, data_context)
        _slide_04_metodologi(prs, data_context)
        _slide_05_akurasi(prs, data_context)
        _slide_06_nsb(prs, data_context)
        _slide_07_akar_masalah(prs, data_context)
        _slide_08_action_plan(prs, data_context)
        _slide_09_kesimpulan(prs, data_context)
        _slide_10_penutup(prs, data_context)
        
        # Save ke buffer
        buf = io.BytesIO()
        prs.save(buf)
        buf.seek(0)
        
        return buf.getvalue()
    except Exception as e:
        print(f"[REI PPT ERROR] {e}")
        import traceback
        print(traceback.format_exc())
        return None