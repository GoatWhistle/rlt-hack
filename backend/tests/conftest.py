import os

import pytest

REQUIRE_CHDB = os.environ.get("REQUIRE_CHDB") == "1"
CHDB_SKIPS: list[str] = []


def _remember(report: pytest.CollectReport | pytest.TestReport) -> None:
    if report.skipped and "chdb" in str(report.longrepr):
        CHDB_SKIPS.append(report.nodeid)


def pytest_collectreport(report: pytest.CollectReport) -> None:
    _remember(report)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    _remember(report)


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if REQUIRE_CHDB and CHDB_SKIPS:
        terminalreporter.write_line(
            f"REQUIRE_CHDB=1, but {len(CHDB_SKIPS)} chDB tests were skipped", red=True
        )


def pytest_sessionfinish(session: pytest.Session) -> None:
    if REQUIRE_CHDB and CHDB_SKIPS:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
