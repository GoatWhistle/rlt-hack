from collections.abc import Sequence
from dataclasses import dataclass, field

from src.models.archive_roster import ArchiveRoster
from src.models.enums import EnrichmentSource, Novelty, WarningCode
from src.models.search_result import SearchWarning
from tests.fakes.domain import make_query
from tests.fakes.ports import PortFailureError
from tests.service.supplier_search.test_service import ALPHA, BETA, Harness


@dataclass
class FakeRoster:
    known: frozenset[str] = frozenset()
    fails: bool = False
    asked: list[tuple[str, ...]] = field(default_factory=list)

    async def roster(self, inns: Sequence[str]) -> ArchiveRoster | None:
        self.asked.append(tuple(inns))
        if self.fails:
            raise PortFailureError("roster")
        return ArchiveRoster("inn-test", self.known & frozenset(inns))


async def test_candidates_outside_the_archive_are_new_and_the_set_is_versioned() -> None:
    roster = FakeRoster(known=frozenset({ALPHA.inn or ""}))
    result = await Harness(roster=roster).service().search(make_query(limit=5))
    novelty = {item.supplier.supplier_id: item.novelty for item in result.candidates}
    assert novelty[ALPHA.supplier_id] == Novelty.KNOWN
    assert novelty[BETA.supplier_id] == (Novelty.NEW if BETA.has_valid_inn else Novelty.UNKNOWN)
    assert result.pipeline.novelty_set == "inn-test"


async def test_roster_outage_leaves_novelty_unknown_with_a_warning() -> None:
    result = await Harness(roster=FakeRoster(fails=True)).service().search(make_query(limit=5))
    assert {item.novelty for item in result.candidates} == {Novelty.UNKNOWN}
    assert result.pipeline.novelty_set == ""
    warning = SearchWarning(WarningCode.ENRICHMENT_FAILED, EnrichmentSource.ARCHIVE)
    assert warning in result.warnings


async def test_without_a_roster_novelty_is_not_claimed() -> None:
    result = await Harness().service().search(make_query(limit=5))
    assert {item.novelty for item in result.candidates} == {Novelty.UNKNOWN}
