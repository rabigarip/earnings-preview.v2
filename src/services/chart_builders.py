"""
Chart builders for PPTX report generation.

Creates embedded charts in python-pptx slides:
- Revenue & Net Income clustered bar chart (3yr history + 3yr forward)
- P/E ratio bar chart with 5-year average reference
"""
from __future__ import annotations

from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.util import Inches, Pt, Emu


# ── Color palette (matches report theme) ──────────────────────────────────
DARK_BLUE = RGBColor(0x1F, 0x3A, 0x5F)
GOLD = RGBColor(0xC9, 0xA2, 0x27)
LIGHT_GOLD = RGBColor(0xE8, 0xD5, 0x8C)
MUTED_GRAY = RGBColor(0x8B, 0x94, 0x9E)
ESTIMATE_BLUE = RGBColor(0x6B, 0x9B, 0xD2)
ESTIMATE_GOLD = RGBColor(0xD4, 0xC0, 0x7A)


def _safe_float(v) -> float:
    """Convert value to float, return 0.0 for None/invalid."""
    if v is None:
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def build_revenue_ni_chart(
    slide,
    x, y, w, h,
    periods: list[str],
    revenues: list[float | None],
    net_incomes: list[float | None],
    actuals_boundary: int,
    currency: str = "",
) -> None:
    """Add clustered bar chart: Revenue (dark blue) + Net Income (gold).

    Args:
        slide: python-pptx slide object
        x, y, w, h: position and size (Inches or Emu)
        periods: ["FY2023", "FY2024", ..., "FY2028"]
        revenues: parallel array of revenue values (in millions)
        net_incomes: parallel array of net income values
        actuals_boundary: index of last actual period (for visual distinction)
        currency: currency code for axis label
    """
    if not periods or (not any(revenues) and not any(net_incomes)):
        return

    chart_data = CategoryChartData()
    chart_data.categories = [p.replace("FY", "") for p in periods]
    chart_data.add_series("Revenue", [_safe_float(v) for v in revenues])
    chart_data.add_series("Net Income", [_safe_float(v) for v in net_incomes])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, w, h, chart_data
    )
    chart = chart_frame.chart

    # Style
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.BOTTOM
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(7)
    chart.legend.font.color.rgb = MUTED_GRAY

    # Revenue series — dark blue
    rev_series = chart.series[0]
    rev_series.format.fill.solid()
    rev_series.format.fill.fore_color.rgb = DARK_BLUE

    # Net Income series — gold
    ni_series = chart.series[1]
    ni_series.format.fill.solid()
    ni_series.format.fill.fore_color.rgb = GOLD

    # Axis styling
    cat_axis = chart.category_axis
    cat_axis.tick_labels.font.size = Pt(7)
    cat_axis.tick_labels.font.color.rgb = MUTED_GRAY
    cat_axis.has_major_gridlines = False
    cat_axis.format.line.fill.background()

    val_axis = chart.value_axis
    val_axis.tick_labels.font.size = Pt(7)
    val_axis.tick_labels.font.color.rgb = MUTED_GRAY
    val_axis.has_major_gridlines = True
    val_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE0, 0xE0, 0xE0)
    val_axis.format.line.fill.background()

    # Remove chart border
    chart_frame.line.fill.background()


def build_pe_chart(
    slide,
    x, y, w, h,
    periods: list[str],
    pe_values: list[float | None],
    five_yr_avg: float | None = None,
) -> None:
    """Bar chart of P/E ratios with optional 5-year average annotation.

    Args:
        slide: python-pptx slide object
        x, y, w, h: position and size
        periods: ["FY2023", ..., "FY2028"]
        pe_values: P/E multiples per period
        five_yr_avg: optional 5-year average for reference annotation
    """
    if not periods or not any(pe_values):
        return

    chart_data = CategoryChartData()
    chart_data.categories = [p.replace("FY", "") for p in periods]
    chart_data.add_series("P/E", [_safe_float(v) for v in pe_values])

    chart_frame = slide.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED, x, y, w, h, chart_data
    )
    chart = chart_frame.chart

    # Style
    chart.has_legend = False

    # P/E series — muted gray
    pe_series = chart.series[0]
    pe_series.format.fill.solid()
    pe_series.format.fill.fore_color.rgb = MUTED_GRAY

    # Axis styling
    cat_axis = chart.category_axis
    cat_axis.tick_labels.font.size = Pt(7)
    cat_axis.tick_labels.font.color.rgb = MUTED_GRAY
    cat_axis.has_major_gridlines = False
    cat_axis.format.line.fill.background()

    val_axis = chart.value_axis
    val_axis.tick_labels.font.size = Pt(7)
    val_axis.tick_labels.font.color.rgb = MUTED_GRAY
    val_axis.has_major_gridlines = True
    val_axis.major_gridlines.format.line.color.rgb = RGBColor(0xE0, 0xE0, 0xE0)
    val_axis.format.line.fill.background()

    # Remove chart border
    chart_frame.line.fill.background()

    # Add 5yr average annotation as a textbox
    if five_yr_avg is not None and five_yr_avg > 0:
        from pptx.enum.text import PP_ALIGN
        txbox = slide.shapes.add_textbox(
            x + Inches(0.1), y + Inches(0.05), w - Inches(0.2), Inches(0.2)
        )
        tf = txbox.text_frame
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.text = f"5yr Avg: {five_yr_avg:.1f}x"
        p.alignment = PP_ALIGN.RIGHT
        if p.runs:
            p.runs[0].font.size = Pt(7)
            p.runs[0].font.color.rgb = RGBColor(0xAA, 0x33, 0xAA)
            p.runs[0].font.bold = True


def build_expanded_table(
    slide,
    x, y,
    periods: list[str],
    announcement_dates: list[str],
    metrics: dict,
    currency: str,
    tx_fn,
    rect_fn,
) -> float:
    """Build a 6-column financial table with actual/estimate shading.

    Args:
        slide: python-pptx slide object
        x, y: top-left position
        periods: ["FY2023", "FY2024", ..., "FY2028"]
        announcement_dates: parallel array to determine actual vs estimate
        metrics: {"net_sales": [...], "ebitda": [...], "ebit": [...], "net_income": [...], "eps": [...]}
        currency: for row labels
        tx_fn: text rendering function from generate_report
        rect_fn: rectangle rendering function from generate_report

    Returns:
        y position after the table (for subsequent elements)
    """
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    if not periods:
        return y

    # Limit to 6 periods max
    periods = periods[-6:] if len(periods) > 6 else periods
    n_cols = len(periods)

    # Align other arrays
    def _tail(arr, n):
        arr = arr or []
        if len(arr) > n:
            return arr[-n:]
        return arr + [None] * (n - len(arr))

    ann_dates = _tail(announcement_dates, n_cols)

    # Determine actual/estimate boundary per column
    is_estimate = []
    for i, d in enumerate(ann_dates):
        is_estimate.append(not d or str(d).strip() in ("", "-", "None"))

    # Column widths
    metric_w = Inches(1.2)
    col_w = Inches(0.85)
    rh = Inches(0.35)

    WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    BLACK = RGBColor(0x1F, 0x23, 0x28)
    HEADER_BG = RGBColor(0x0D, 0x11, 0x17)
    ACTUAL_BG = RGBColor(0xF5, 0xF5, 0xF5)
    ESTIMATE_BG = RGBColor(0xE8, 0xF0, 0xFA)
    BORDER = RGBColor(0xDB, 0xE0, 0xE6)
    MUTED = RGBColor(0x8B, 0x94, 0x9E)

    # Header row
    cx = x
    rect_fn(slide, cx, y, metric_w, rh, HEADER_BG, BORDER)
    tx_fn(slide, cx + Inches(0.05), y + Inches(0.05), metric_w - Inches(0.1), rh, "Metric", sz=8, bold=True, rgb=WHITE)
    cx += metric_w
    for i, p in enumerate(periods):
        label = p.replace("FY", "")
        suffix = "(E)" if is_estimate[i] else "(A)"
        bg = ESTIMATE_BG if is_estimate[i] else ACTUAL_BG
        rect_fn(slide, cx, y, col_w, rh, HEADER_BG, BORDER)
        tx_fn(slide, cx + Inches(0.03), y + Inches(0.05), col_w - Inches(0.06), rh, f"{label}{suffix}", sz=7, bold=True, rgb=WHITE, al=PP_ALIGN.CENTER)
        cx += col_w

    # Data rows
    _cM = f"({currency}M)" if currency else "(M)"
    _cU = f"({currency})" if currency else ""
    row_defs = [
        (f"Revenue {_cM}", "net_sales"),
        (f"EBITDA {_cM}", "ebitda"),
        (f"EBIT {_cM}", "ebit"),
        (f"Net Income {_cM}", "net_income"),
        (f"EPS {_cU}", "eps"),
    ]

    for ri, (label, key) in enumerate(row_defs):
        row_y = y + rh * (ri + 1)
        vals = _tail(metrics.get(key), n_cols)

        # Skip row if ALL values are None
        if all(v is None for v in vals):
            continue

        cx = x
        rect_fn(slide, cx, row_y, metric_w, rh, WHITE, BORDER)
        tx_fn(slide, cx + Inches(0.05), row_y + Inches(0.05), metric_w - Inches(0.1), rh, label, sz=7, bold=True, rgb=BLACK)
        cx += metric_w

        for i, v in enumerate(vals):
            bg = ESTIMATE_BG if is_estimate[i] else ACTUAL_BG
            rect_fn(slide, cx, row_y, col_w, rh, bg, BORDER)
            # Format value
            if v is None:
                display = "—"
            elif key == "eps":
                display = f"{v:.2f}" if isinstance(v, (int, float)) else str(v)
            else:
                try:
                    fv = float(v)
                    display = f"{fv:,.0f}" if abs(fv) >= 1 else f"{fv:.2f}"
                except (TypeError, ValueError):
                    display = str(v)
            tx_fn(slide, cx + Inches(0.03), row_y + Inches(0.05), col_w - Inches(0.06), rh, display, sz=7, rgb=BLACK, al=PP_ALIGN.CENTER)
            cx += col_w

    # Return y after table
    n_data_rows = sum(1 for _, key in row_defs if any(v is not None for v in _tail(metrics.get(key), n_cols)))
    return y + rh * (n_data_rows + 1) + Inches(0.15)
