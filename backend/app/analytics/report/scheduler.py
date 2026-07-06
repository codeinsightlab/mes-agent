import logging
import threading
from datetime import datetime, time, timedelta

from app.analytics.report.report_generator import MdReportGenerator


logger = logging.getLogger(__name__)
DAILY_REPORT_TIME = time(hour=0, minute=10)


class DailyReportScheduler:
    def __init__(self, generator: MdReportGenerator):
        self._generator = generator
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="analytics-report-scheduler",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            delay = seconds_until_next_daily_run(datetime.now())
            if self._stop_event.wait(delay):
                return
            try:
                self._generator.generate_daily_reports()
            except Exception as exc:
                logger.error(
                    "Analytics report scheduler failed exception_type=%s",
                    type(exc).__name__,
                )


def seconds_until_next_daily_run(now: datetime) -> float:
    next_run = datetime.combine(now.date(), DAILY_REPORT_TIME)
    if now >= next_run:
        next_run += timedelta(days=1)
    return max((next_run - now).total_seconds(), 0.0)
