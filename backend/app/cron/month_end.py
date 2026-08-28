"""
Month-end filing cron entrypoint.

Render Cron Job schedule: 0 6 18 * *  (18th of every month, 06:00 UTC / 09:00 EAT).
Files the previous calendar month against TOT or NIL so the 20th KRA deadline is met.
"""

from __future__ import annotations

import json
import logging
import sys

from sqlmodel import Session

from app.database import engine, init_db
from app.services.filing_engine import FilingEngine, previous_tax_period

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("jibutax.cron.month_end")


def main() -> int:
    init_db()
    year, month = previous_tax_period()
    logger.info("Starting month-end filing for %s-%02d", year, month)
    with Session(engine) as session:
        filings = FilingEngine(session).run_month_end()
        summary = [
            {
                "trader_pin": row.trader_pin,
                "return_kind": row.return_kind.value,
                "status": row.status.value,
                "invoice_count": row.invoice_count,
                "gross_turnover": str(row.gross_turnover),
                "ack_number": row.ack_number,
                "error": row.error_message,
            }
            for row in filings
        ]
    logger.info("Month-end filing complete: %s", json.dumps(summary))
    failures = [row for row in filings if row.status.value == "ERROR"]
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
