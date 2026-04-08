"""
Source merger — merges Bloomberg, MarketScreener, and Yahoo Finance data.

Priority: Bloomberg (when uploaded) > MarketScreener > Yahoo Finance.
Flags divergences >10% between sources.
"""
from __future__ import annotations
import logging

log = logging.getLogger(__name__)

DIVERGENCE_THRESHOLD = 0.10  # 10%


def merge_sources(
    bbg: dict | None,
    ms_consensus: dict | None,
    ms_annual: dict | None,
    yahoo_quote: object | None,
    first_est_period: str | None = None,
) -> dict:
    """Merge Bloomberg + MS + Yahoo with Bloomberg as primary.

    Args:
        bbg: parsed Bloomberg data (from bloomberg_parser)
        ms_consensus: payload.consensus_summary
        ms_annual: ms_annual_forecasts.annual
        yahoo_quote: payload.quote
        first_est_period: e.g. "FY2026" to pick the right MS column

    Returns:
        {
            'rating': {value, source},
            'target_price': {value, source},
            'revenue': {primary: {value, source}, alt: {value, source}, divergence_pct},
            'ebitda': {...},
            'eps': {...},
            'net_income': {...},
            'broker_table': [{name, analyst, revenue, eps, net_income}],
            'divergences': [{metric, bbg_val, ms_val, pct}],
        }
    """
    result = {
        "rating": {"value": None, "source": None},
        "target_price": {"value": None, "source": None},
        "revenue": {},
        "ebitda": {},
        "eps": {},
        "net_income": {},
        "broker_table": [],
        "divergences": [],
    }

    ms_consensus = ms_consensus or {}
    ms_annual = ms_annual or {}

    # Find MS estimate values for the target period
    ms_periods = ms_annual.get("periods") or []
    ms_est_idx = -1
    if first_est_period:
        for i, p in enumerate(ms_periods):
            if first_est_period in str(p):
                ms_est_idx = i
                break

    def _ms_val(key):
        arr = ms_annual.get(key) or []
        if 0 <= ms_est_idx < len(arr):
            return arr[ms_est_idx]
        return None

    # ── Rating ──
    if bbg and bbg.get("consensus"):
        # Bloomberg doesn't typically have rating in MODL, use MS
        pass
    if ms_consensus.get("consensus_rating"):
        result["rating"] = {"value": ms_consensus["consensus_rating"], "source": "MS"}
    elif yahoo_quote and getattr(yahoo_quote, "recommendation_key", None):
        rec = getattr(yahoo_quote, "recommendation_key", "")
        if rec and rec != "none":
            result["rating"] = {"value": rec.upper().replace("_", " "), "source": "Yahoo"}

    # ── Target Price ──
    if ms_consensus.get("average_target_price"):
        result["target_price"] = {"value": ms_consensus["average_target_price"], "source": "MS"}
    elif yahoo_quote and getattr(yahoo_quote, "target_mean_price", None):
        result["target_price"] = {"value": yahoo_quote.target_mean_price, "source": "Yahoo"}

    # ── Key metrics: BBG primary, MS fallback ──
    metrics = ["revenue", "ebitda", "eps", "net_income"]
    ms_keys = {"revenue": "net_sales", "ebitda": "ebitda", "eps": "eps", "net_income": "net_income"}

    for metric in metrics:
        primary = None
        primary_src = None
        alt = None
        alt_src = None

        if bbg:
            bbg_cons = (bbg.get("consensus") or {}).get(metric, {})
            if bbg_cons.get("mean") is not None:
                primary = bbg_cons["mean"]
                primary_src = "BBG"

        ms_v = _ms_val(ms_keys.get(metric, metric))
        if ms_v is not None:
            if primary is None:
                primary = ms_v
                primary_src = "MS"
            else:
                alt = ms_v
                alt_src = "MS"

        result[metric] = {
            "primary": {"value": primary, "source": primary_src},
            "alt": {"value": alt, "source": alt_src} if alt is not None else None,
        }

        # Check divergence
        if primary is not None and alt is not None and alt != 0:
            pct = abs(primary - alt) / abs(alt)
            if pct > DIVERGENCE_THRESHOLD:
                result["divergences"].append({
                    "metric": metric,
                    "bbg_val": primary if primary_src == "BBG" else alt,
                    "ms_val": alt if alt_src == "MS" else primary,
                    "pct": round(pct * 100, 1),
                })
                result[metric]["divergence_pct"] = round(pct * 100, 1)

    # ── Broker table (from Bloomberg) ──
    if bbg:
        for broker in bbg.get("brokers") or []:
            row = {
                "name": broker.get("name", ""),
                "analyst": broker.get("analyst", ""),
            }
            for metric in metrics:
                row[metric] = broker.get("estimates", {}).get(metric)
            result["broker_table"].append(row)

    if result["divergences"]:
        log.warning("Source divergences: %s", result["divergences"])

    return result
