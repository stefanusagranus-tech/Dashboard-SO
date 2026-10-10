def _build_infografis(data):
    from pictex import Canvas, Row, Column, Text

    _W = 1000  # lebar konten (1080 - 2*40 padding)

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
        .width(_W)
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
        ).width(320).padding(25).background_color("#D2E0D3").border_radius(12).gap(6),

        Column(
            Text("TOTAL ITEM").font_size(14).color("#3C3C3C").font_weight("bold"),
            Text(f"{data['total_item']} item").font_size(32).color("#3C3C3C").font_weight("bold"),
        ).width(320).padding(25).background_color("#F0DDD6").border_radius(12).gap(6),

        Column(
            Text("TOTAL NOMINAL").font_size(14).color("#3C3C3C").font_weight("bold"),
            Text(_fmt_rp(data['total_nominal'])).font_size(32).color("#3C3C3C").font_weight("bold"),
        ).width(320).padding(25).background_color("#F2C3B9").border_radius(12).gap(6),
    ).gap(20)

    # === RINGKASAN ===
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
        .width(_W)
        .padding(25)
        .background_color("#FFFFFF")
        .border_radius(12)
        .gap(8)
    )

    # === INSIGHT ===
    insight = (
        Column(
            Text("INSIGHT").font_size(18).color("#3C3C3C").font_weight("bold"),
            Text(data["insight"]).font_size(14).color("#3C3C3C"),
        )
        .width(_W)
        .padding(25)
        .background_color("#F0EEEA")
        .border_radius(12)
        .gap(10)
    )

    # === TABEL RAK ===
    _col_w = [120, 400, 200, 240]  # total 960 (dalam padding)

    _header_cells = Row(
        Text("RAK").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).width(_col_w[0]),
        Text("NAMA RAK").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).width(_col_w[1]),
        Text("PIC").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).width(_col_w[2]),
        Text("SELISIH").font_size(14).color("#FFFFFF").font_weight("bold").padding(12).width(_col_w[3]),
    ).background_color("#97B3AE")

    _rows = [_header_cells]
    for _i, _r in enumerate(data["list_rak"]):
        _bg = "#F0EEEA" if _i % 2 == 0 else "#FFFFFF"
        _color = "#C83232" if _r["nominal"] < 0 else "#329632"
        _rows.append(
            Row(
                Text(_r["rak_id"]).font_size(14).color("#3C3C3C").padding(12).width(_col_w[0]),
                Text(_r["nama"]).font_size(14).color("#3C3C3C").padding(12).width(_col_w[1]),
                Text(_r["pic"]).font_size(14).color("#3C3C3C").padding(12).width(_col_w[2]),
                Text(_fmt_rp(_r["nominal"])).font_size(14).color(_color).font_weight("bold").padding(12).width(_col_w[3]),
            ).background_color(_bg)
        )

    tabel_rak = Column(*_rows).background_color("#FFFFFF")

    # === SUSUN LAYOUT ===
    layout = Column(
        header,
        kpi_row,
        ringkasan,
        insight,
        tabel_rak,
    ).width(_W).gap(20)

    return canvas.render(layout)
