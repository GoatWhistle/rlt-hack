from datetime import UTC, datetime, timedelta

from src.adapter.system.clock import SystemClock
from src.adapter.system.ids import Uuid4Generator


def test_clock_reports_current_utc_time() -> None:
    moment = SystemClock().now()
    assert moment.tzinfo == UTC
    assert abs(datetime.now(UTC) - moment) < timedelta(seconds=5)


def test_ids_are_random_version_four() -> None:
    ids = Uuid4Generator()
    first, second = ids.new(), ids.new()
    assert first != second
    assert first.version == 4
