"""
Earnings surprise history — computes beat/miss track record from MS quarterly results.

Parses ms_quarterly_results_table (from MS /calendar/ page) to show
how many times the company beat or missed consensus in recent quarters.
"""
from __future__ import annotations


def compute_surprise_history(quarterly_results: dict | None, metric: str = "net_income") -> dict:
    """Compute beat/miss record from MS quarterly results table.

    Args:
        quarterly_results: ms_quarterly_results_table from payload
            Expected structure: {quarters: [...], rows: [{metric_key, released: [...], forecast: [...], spread_pct: [...]}]}
        metric: which metric to analyze ("net_income", "net_sales", "eps")

    Returns:
        {
            beat_count: int,
            miss_count: int,
            inline_count: int,
            total_quarters: int,
            summary: str,           # "Beat 3/4 quarters"
            avg_surprise_pct: float | None,
            details: [{quarter, actual, estimate, surprise_pct}]
        }
    """
    result = {
        "beat_count": 0,
        "miss_count": 0,
        "inline_count": 0,
        "total_quarters": 0,
        "summary": "",
        "avg_surprise_pct": None,
        "details": [],
    }

    if not quarterly_results or not isinstance(quarterly_results, dict):
        return result

    quarters = quarterly_results.get("quarters") or []
    rows_list = quarterly_results.get("rows") or []
    if not quarters or not rows_list:
        return result

    # Find the target metric row
    target_row = None
    for row in rows_list:
        if not isinstance(row, dict):
            continue
        mk = (row.get("metric_key") or "").lower()
        if metric.lower() in mk or mk in metric.lower():
            target_row = row
            break

    if not target_row:
        # Try broader match
        for row in rows_list:
            if not isinstance(row, dict):
                continue
            ml = (row.get("metric_label") or "").lower()
            if metric.lower().replace("_", " ") in ml:
                target_row = row
                break

    if not target_row:
        return result

    released = target_row.get("released") or []
    forecast = target_row.get("forecast") or []
    spread = target_row.get("spread_pct") or []

    surprises = []
    for i in range(min(len(quarters), len(released), len(forecast))):
        act = released[i]
        est = forecast[i]
        spr = spread[i] if i < len(spread) else None

        if act is None or est is None:
            continue

        try:
            act_f = float(act)
            est_f = float(est)
        except (TypeError, ValueError):
            continue

        if spr is None and est_f != 0:
            spr = round((act_f - est_f) / abs(est_f) * 100, 1)

        detail = {
            "quarter": quarters[i] if i < len(quarters) else f"Q{i+1}",
            "actual": act_f,
            "estimate": est_f,
            "surprise_pct": spr,
        }
        surprises.append(detail)

    if not surprises:
        return result

    # Take last 8 quarters max
    surprises = surprises[-8:]

    beats = sum(1 for s in surprises if s["surprise_pct"] is not None and s["surprise_pct"] > 1.0)
    misses = sum(1 for s in surprises if s["surprise_pct"] is not None and s["surprise_pct"] < -1.0)
    inline = len(surprises) - beats - misses

    valid_surprises = [s["surprise_pct"] for s in surprises if s["surprise_pct"] is not None]
    avg = round(sum(valid_surprises) / len(valid_surprises), 1) if valid_surprises else None

    total = len(surprises)
    if beats > misses:
        summary = f"Beat {beats}/{total} quarters"
    elif misses > beats:
        summary = f"Missed {misses}/{total} quarters"
    else:
        summary = f"Mixed: {beats} beat, {misses} miss of {total}"

    if avg is not None:
        summary += f" (avg {avg:+.1f}%)"

    return {
        "beat_count": beats,
        "miss_count": misses,
        "inline_count": inline,
        "total_quarters": total,
        "summary": summary,
        "avg_surprise_pct": avg,
        "details": surprises,
    }
