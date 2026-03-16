"""Generador de Reporte Ejecutivo PDF — 1 página para gerencia."""
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

# ── Constantes de diseño ──────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4          # 595.27 x 841.89 pt
MARGIN_X = 36                # margen izquierdo / derecho
CONTENT_W = PAGE_W - 2 * MARGIN_X

# Paleta corporativa
C_BLUE   = colors.HexColor("#1E40AF")   # azul primario
C_BLUE_L = colors.HexColor("#EFF6FF")   # azul muy claro
C_GREEN  = colors.HexColor("#059669")   # verde éxito
C_GREEN_L= colors.HexColor("#ECFDF5")
C_GRAY   = colors.HexColor("#6B7280")
C_DARK   = colors.HexColor("#111827")
C_WHITE  = colors.white
C_AMBER  = colors.HexColor("#D97706")
C_PURPLE = colors.HexColor("#7C3AED")
C_LINE   = colors.HexColor("#E5E7EB")


def _fmt_cop(value: float) -> str:
    """Formatea un número como moneda COP abreviada."""
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B COP"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M COP"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K COP"
    return f"${value:,.0f} COP"


def _draw_rounded_rect(c: canvas.Canvas, x, y, w, h, radius=6,
                        fill_color=None, stroke_color=None, stroke_width=1):
    """Dibuja un rectángulo con esquinas redondeadas."""
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    else:
        c.setStrokeColor(colors.transparent)
    c.roundRect(x, y, w, h, radius, fill=1 if fill_color else 0,
                stroke=1 if stroke_color else 0)


def generate_executive_report(
    periodo_label: str,
    ahorro_mes: float,
    ahorro_anual: float,
    roi: float,
    historias_auditadas: int,
    tendencia_mensual: List[Dict[str, Any]],
    top_modulos: List[Dict[str, Any]],
    generado_por: str,
) -> bytes:
    """
    Genera un Reporte Ejecutivo PDF de 1 página.

    Args:
        periodo_label: Ej. "Marzo 2026"
        ahorro_mes: Ahorro del período en COP
        ahorro_anual: Ahorro acumulado anual en COP
        roi: ROI del período (porcentaje)
        historias_auditadas: Número de historias procesadas
        tendencia_mensual: [{"label": "Oct", "valor": 1500000}, ...]  (últimos 6 meses)
        top_modulos: [{"nombre": "Estancia prolongada", "porcentaje": 42, "valor": 20400000}, ...]
        generado_por: Nombre del usuario que genera el reporte
    Returns:
        bytes del PDF
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Reporte Ejecutivo AudiMedIA — {periodo_label}")

    # ── 1. HEADER BAND ────────────────────────────────────────────────────────
    header_h = 76
    header_y = PAGE_H - header_h
    c.setFillColor(C_BLUE)
    c.rect(0, header_y, PAGE_W, header_h, fill=1, stroke=0)

    # Logo text
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(MARGIN_X, PAGE_H - 32, "AudiMedIA")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#BFDBFE"))
    c.drawString(MARGIN_X, PAGE_H - 46, "Plataforma de Auditoría Médica Inteligente")

    # Título centrado
    c.setFillColor(C_WHITE)
    c.setFont("Helvetica-Bold", 14)
    title_text = "Reporte Ejecutivo de Auditoría Médica"
    c.drawCentredString(PAGE_W / 2, PAGE_H - 28, title_text)
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#BFDBFE"))
    c.drawCentredString(PAGE_W / 2, PAGE_H - 44, f"Período: {periodo_label}")

    # Fecha a la derecha
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#BFDBFE"))
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 28, datetime.now().strftime("%d/%m/%Y %H:%M"))
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 42, f"Generado por: {generado_por}")

    # ── 2. CIFRAS DESTACADAS ──────────────────────────────────────────────────
    kpi_y = header_y - 16
    kpi_h = 90
    kpi_gap = 10
    kpi_w = (CONTENT_W - 3 * kpi_gap) / 4

    kpis = [
        {
            "label": "💰 Ahorro del mes",
            "value": _fmt_cop(ahorro_mes),
            "sub": "Período actual",
            "bg": C_GREEN_L,
            "fg": C_GREEN,
        },
        {
            "label": "📊 Acumulado anual",
            "value": _fmt_cop(ahorro_anual),
            "sub": f"Año {datetime.now().year}",
            "bg": C_BLUE_L,
            "fg": C_BLUE,
        },
        {
            "label": "🔄 ROI del período",
            "value": f"{roi:+.1f}%",
            "sub": "Retorno inversión",
            "bg": colors.HexColor("#FFF7ED"),
            "fg": C_AMBER,
        },
        {
            "label": "📋 Historias",
            "value": str(historias_auditadas),
            "sub": "Auditadas",
            "bg": colors.HexColor("#F5F3FF"),
            "fg": C_PURPLE,
        },
    ]

    for i, kpi in enumerate(kpis):
        bx = MARGIN_X + i * (kpi_w + kpi_gap)
        by = kpi_y - kpi_h
        _draw_rounded_rect(c, bx, by, kpi_w, kpi_h, radius=8,
                           fill_color=kpi["bg"], stroke_color=C_LINE, stroke_width=1)
        # label
        c.setFillColor(C_GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(bx + 10, by + kpi_h - 18, kpi["label"])
        # value (big)
        c.setFillColor(kpi["fg"])
        val = kpi["value"]
        font_size = 16 if len(val) < 12 else 13
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(bx + 10, by + kpi_h - 48, val)
        # sub
        c.setFillColor(C_GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(bx + 10, by + 10, kpi["sub"])

    section_y = kpi_y - kpi_h - 16

    # ── 3. GRÁFICO DE TENDENCIA ───────────────────────────────────────────────
    chart_label_y = section_y
    c.setFillColor(C_DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN_X, chart_label_y, "Tendencia — Ahorro mensual (últimos 6 meses)")
    c.setFillColor(C_GRAY)
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN_X, chart_label_y, "Eje: millones COP")

    chart_area_y = chart_label_y - 130
    chart_h = 115
    chart_w = CONTENT_W

    # Fondo del gráfico
    _draw_rounded_rect(c, MARGIN_X, chart_area_y, chart_w, chart_h, radius=6,
                       fill_color=colors.HexColor("#F9FAFB"), stroke_color=C_LINE)

    if tendencia_mensual:
        max_val = max((m.get("valor", 0) for m in tendencia_mensual), default=1) or 1
        n = len(tendencia_mensual)
        bar_zone_w = chart_w - 60   # espacio a la izquierda para eje Y
        bar_zone_x = MARGIN_X + 52
        bar_area_h = chart_h - 30   # espacio inferior para etiquetas
        bar_area_y = chart_area_y + 20

        bar_w = (bar_zone_w / n) * 0.55
        bar_gap = (bar_zone_w / n) * 0.45

        # Líneas de referencia horizontal (4 niveles)
        for lvl in range(5):
            ly = bar_area_y + (lvl / 4) * bar_area_h
            c.setStrokeColor(C_LINE)
            c.setLineWidth(0.5)
            c.line(bar_zone_x, ly, bar_zone_x + bar_zone_w, ly)
            # Etiqueta eje Y
            lv = (lvl / 4) * max_val
            c.setFillColor(C_GRAY)
            c.setFont("Helvetica", 7)
            c.drawRightString(bar_zone_x - 4, ly - 3, _fmt_cop(lv).replace(" COP", ""))

        for i, mes in enumerate(tendencia_mensual):
            valor = mes.get("valor", 0)
            bx = bar_zone_x + i * (bar_w + bar_gap)
            bh = (valor / max_val) * bar_area_h if max_val > 0 else 2
            bh = max(bh, 2)

            # Barra con gradiente visual (rectángulo sólido)
            c.setFillColor(C_BLUE)
            c.roundRect(bx, bar_area_y, bar_w, bh, 3, fill=1, stroke=0)

            # Valor sobre la barra
            c.setFillColor(C_DARK)
            c.setFont("Helvetica-Bold", 7)
            label_v = _fmt_cop(valor).replace(" COP", "")
            c.drawCentredString(bx + bar_w / 2, bar_area_y + bh + 3, label_v)

            # Etiqueta mes
            c.setFillColor(C_GRAY)
            c.setFont("Helvetica", 7)
            c.drawCentredString(bx + bar_w / 2, chart_area_y + 5, mes.get("label", ""))

    section_y = chart_area_y - 16

    # ── 4. TOP CAUSAS DE GLOSA ────────────────────────────────────────────────
    c.setFillColor(C_DARK)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN_X, section_y, "Top causas de glosa detectadas")

    causes_y = section_y - 14
    modulo_colors = [C_AMBER, C_BLUE, C_GREEN, C_PURPLE]
    row_h = 22
    half_w = CONTENT_W / 2 - 8

    modulos_to_show = top_modulos[:4] if top_modulos else []
    for i, mod in enumerate(modulos_to_show):
        col = i % 2
        row = i // 2
        bx = MARGIN_X + col * (half_w + 16)
        by = causes_y - row * (row_h + 8) - row_h

        bar_color = modulo_colors[i % len(modulo_colors)]
        _draw_rounded_rect(c, bx, by, half_w, row_h, radius=4,
                           fill_color=colors.HexColor("#F9FAFB"), stroke_color=C_LINE)

        # Bija de color
        c.setFillColor(bar_color)
        c.roundRect(bx + 8, by + 6, 6, 10, 2, fill=1, stroke=0)

        # Nombre
        c.setFillColor(C_DARK)
        c.setFont("Helvetica", 8)
        nombre = mod.get("nombre", "")
        if len(nombre) > 28:
            nombre = nombre[:26] + "…"
        c.drawString(bx + 20, by + 8, nombre)

        # Porcentaje
        pct = mod.get("porcentaje", 0)
        c.setFillColor(bar_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(bx + half_w - 8, by + 8, f"{pct:.0f}%")

    rows_used = (len(modulos_to_show) + 1) // 2
    section_y = causes_y - rows_used * (row_h + 8) - 16

    # ── 5. ROI DESTACADO ──────────────────────────────────────────────────────
    roi_h = 52
    roi_box_y = section_y - roi_h

    # Fondo azul claro con borde
    _draw_rounded_rect(c, MARGIN_X, roi_box_y, CONTENT_W, roi_h, radius=8,
                       fill_color=C_BLUE_L, stroke_color=C_BLUE, stroke_width=1)

    roi_x1 = 1 + (roi / 100) if roi > 0 else 1
    c.setFillColor(C_BLUE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(PAGE_W / 2, roi_box_y + roi_h - 20,
                        "Indicador de Retorno de Inversión (ROI)")
    c.setFont("Helvetica", 10)
    c.setFillColor(C_DARK)
    ratio_text = (
        f"Por cada $1 invertido en AudiMedIA, "
        f"la institución evitó ${roi_x1:.1f} en glosas  —  ROI: {roi:+.1f}%"
    )
    c.drawCentredString(PAGE_W / 2, roi_box_y + 12, ratio_text)

    # ── 6. FOOTER ─────────────────────────────────────────────────────────────
    footer_h = 28
    footer_y = 0
    c.setFillColor(colors.HexColor("#F3F4F6"))
    c.rect(0, footer_y, PAGE_W, footer_h, fill=1, stroke=0)

    c.setFillColor(C_GRAY)
    c.setFont("Helvetica", 8)
    c.drawString(MARGIN_X, footer_y + 10,
                 f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}  |  "
                 f"Por: {generado_por}  |  AudiMedIA — Sistema de Auditoría Médica Inteligente")
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(C_BLUE)
    c.drawRightString(PAGE_W - MARGIN_X, footer_y + 10, "© AudiMedIA 2026")

    # ── Línea separadora del footer ───────────────────────────────────────────
    c.setStrokeColor(C_LINE)
    c.setLineWidth(1)
    c.line(0, footer_h, PAGE_W, footer_h)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()
