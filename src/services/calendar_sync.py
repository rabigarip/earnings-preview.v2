"""
Earnings calendar sync — populates the earnings_calendar DB table.

Fetches next earnings dates from the pipeline's existing data sources
(MS /calendar/ page + Yahoo earnings_dates) for all seeded tickers.
"""
from __future__ import annotations
import logging
import time

log = logging.getLogger(__name__)


def sync_calendar_for_ticker(ticker: str) -> dict | None:
    """Fetch and store next earnings date for one ticker.

    Uses the lightweight path: Yahoo earnings_dates first,
    then MS calendar page if available.

    Returns {ticker, next_earnings_date, source} or None.
    """
    from src.storage.db import load_company, upsert_earnings_date

    company = load_company(ticker)
    if not company:
        return None

    name = company.get("company_name", ticker)
    country = company.get("country", "")
    sector = company.get("sector", "")
    next_date = None
    label = ""
    source = ""

    # Try Yahoo first (fastest)
    try:
        from src.providers.yahoo import fetch_next_earnings_date
        yd = fetch_next_earnings_date(ticker)
        if yd and isinstance(yd, dict) and yd.get("next_earnings_date"):
            next_date = yd["next_earnings_date"]
            source = "yahoo"
    except Exception:
        pass

    # Try MS calendar page if Yahoo failed and company has MS slug
    if not next_date and company.get("marketscreener_company_url"):
        try:
            from src.providers.marketscreener_pages import fetch_calendar_events
            cal, _ = fetch_calendar_events(company["marketscreener_company_url"])
            if cal and cal.get("next_expected_earnings_date"):
                next_date = cal["next_expected_earnings_date"]
                label = cal.get("next_expected_earnings_label", "")
                source = "marketscreener"
        except Exception:
            pass

    upsert_earnings_date(ticker, name, country, sector, next_date, label, source)

    if next_date:
        return {"ticker": ticker, "next_earnings_date": next_date, "source": source}
    return None


def sync_all_calendars(batch_size: int = 50, delay: float = 0.5) -> dict:
    """Batch-update earnings dates for all seeded tickers.

    Returns {synced: int, failed: int, total: int}
    """
    from src.storage.db import list_companies

    companies = list_companies()
    total = len(companies)
    synced = 0
    failed = 0

    for i, comp in enumerate(companies):
        tk = comp.get("ticker", "")
        if not tk:
            continue
        try:
            result = sync_calendar_for_ticker(tk)
            if result:
                synced += 1
            else:
                failed += 1
        except Exception as e:
            log.debug("Calendar sync failed for %s: %s", tk, e)
            failed += 1

        if (i + 1) % batch_size == 0:
            log.info("Calendar sync progress: %d/%d (synced=%d)", i + 1, total, synced)
            time.sleep(delay)  # Rate limit

    log.info("Calendar sync complete: %d synced, %d failed, %d total", synced, failed, total)
    return {"synced": synced, "failed": failed, "total": total}
