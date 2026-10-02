import pytest

from src.models.enums import RequirementStatus
from src.models.errors import InvalidRequirementError
from src.models.requirement import (
    Requirement,
    RequirementCheck,
    check_requirements,
    extract_requirements,
)


def keys(text: str) -> list[tuple[str, str]]:
    return [(need.key, need.value) for need in extract_requirements(text)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Бумага офисная А4 80 г/м2 белая", [("format", "A4"), ("г/м2", "80 г/м2")]),
        ("бумага a4, плотность 80 г/кв. м", [("format", "A4"), ("г/м2", "80 г/м2")]),
        ("Кабель ГОСТ Р 53769-2010", [("gost", "ГОСТ Р53769-2010")]),
        ("Светильник 36 Вт 220 В", [("Вт", "36 Вт"), ("В", "220 В")]),
        ("Экран 15,6 дюйма 16 ГБ", [("ГБ", "16 ГБ"), ("дюйм", "15.6 дюйм")]),
        ("Крупа гречневая 500 кг", []),
        ("Ватман А1 и А1", [("format", "A1")]),
    ],
)
def test_requirements_are_extracted_conservatively(
    text: str, expected: list[tuple[str, str]]
) -> None:
    assert sorted(keys(text)) == sorted(expected)


def test_offer_is_met_conflicting_or_silent_per_requirement() -> None:
    needs = extract_requirements("Бумага А4 80 г/м2 ГОСТ 6656-76")
    met = check_requirements(needs, ["SvetoCopy A4 80г/м2", "ГОСТ 6656-76"])
    assert [check.status for check in met] == [RequirementStatus.MET] * 3
    other = check_requirements(needs, ["Снегурочка А3 65 г/м2 ГОСТ 1-11"])
    statuses = {check.requirement.key: (check.status, check.found) for check in other}
    assert statuses["format"] == (RequirementStatus.CONFLICT, "A3")
    assert statuses["г/м2"] == (RequirementStatus.CONFLICT, "65 г/м2")
    assert statuses["gost"] == (RequirementStatus.UNKNOWN, "")
    silent = check_requirements(needs, ["Бумага офисная"])
    assert {check.status for check in silent} == {RequirementStatus.UNKNOWN}


def test_checks_keep_their_invariants() -> None:
    need = Requirement("format", "A4", "А4")
    with pytest.raises(InvalidRequirementError):
        RequirementCheck(need, RequirementStatus.UNKNOWN, "A4")
    with pytest.raises(InvalidRequirementError):
        RequirementCheck(need, RequirementStatus.MET)
    with pytest.raises(InvalidRequirementError):
        Requirement("", "A4", "А4")
