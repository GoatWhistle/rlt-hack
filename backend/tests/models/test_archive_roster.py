from dataclasses import replace

import pytest

from src.models.archive_roster import ArchiveRoster, RosterSnapshot
from src.models.enums import CandidateOrigin, Novelty
from src.models.errors import InvalidArchiveRosterError
from src.models.scoring import ChannelRank
from tests.fakes.domain import make_candidate


def test_novelty_needs_a_valid_inn_and_the_archive_set() -> None:
    roster = ArchiveRoster("inn-1", frozenset({"7801234564"}))
    assert roster.novelty_of("7801234564") == Novelty.KNOWN
    assert roster.novelty_of("7707083893") == Novelty.NEW
    assert roster.novelty_of("7707083894") == Novelty.UNKNOWN
    assert roster.novelty_of(None) == Novelty.UNKNOWN
    with pytest.raises(InvalidArchiveRosterError):
        ArchiveRoster("", frozenset())


def test_snapshot_keeps_only_checksummed_inns() -> None:
    snapshot = RosterSnapshot.of("v", ["7801234564", "0000000000", "123"])
    assert snapshot.inns == frozenset({"7801234564"})
    with pytest.raises(InvalidArchiveRosterError):
        RosterSnapshot.of("v", ["bad"])


def test_origins_follow_the_channels_that_found_the_candidate() -> None:
    candidate = make_candidate()
    ranks = (ChannelRank("semantic", 3), ChannelRank("lexical", 1), ChannelRank("other", 2))
    both = replace(candidate, score=replace(candidate.score, channels=ranks))
    assert both.origins == (CandidateOrigin.CATALOG, CandidateOrigin.HISTORY)
    history = replace(candidate, score=replace(candidate.score, channels=ranks[:1]))
    assert history.origins == (CandidateOrigin.HISTORY,)
    assert replace(candidate, score=replace(candidate.score, channels=())).origins == ()
