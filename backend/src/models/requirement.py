import re
from collections.abc import Iterable
from dataclasses import dataclass

from src.models.enums import RequirementStatus
from src.models.errors import InvalidRequirementError

FORMAT = re.compile(r"(?<![\w])[AaАа]\s?([0-6])(?![\w])")
MEASURE = re.compile(
    r"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*"
    r"(г/м2|г/м²|г/кв\.?\s?м|мм|см|квт|вт|мач|гб|тб|дюйм(?:а|ов)?|в)(?![\w/])",
    re.IGNORECASE,
)
GOST = re.compile(r"гост\s*(р\s*)?(\d+(?:\.\d+)*-\d{2,4})", re.IGNORECASE)
UNITS = {
    "г/м2": "г/м2",
    "г/м²": "г/м2",
    "мм": "мм",
    "см": "см",
    "квт": "кВт",
    "вт": "Вт",
    "мач": "мАч",
    "гб": "ГБ",
    "тб": "ТБ",
    "в": "В",
}


@dataclass(frozen=True, slots=True)
class Requirement:
    key: str
    value: str
    text: str

    def __post_init__(self) -> None:
        if not self.key or not self.value:
            raise InvalidRequirementError("requirement needs a key and a value")


@dataclass(frozen=True, slots=True)
class RequirementCheck:
    requirement: Requirement
    status: RequirementStatus
    found: str = ""

    def __post_init__(self) -> None:
        if self.status == RequirementStatus.UNKNOWN and self.found:
            raise InvalidRequirementError("an unknown requirement has no found value")
        if self.status != RequirementStatus.UNKNOWN and not self.found:
            raise InvalidRequirementError("a checked requirement keeps the found value")


def _unit(raw: str) -> str:
    lowered = raw.lower().replace(" ", "")
    if lowered.startswith("г/кв"):
        return "г/м2"
    if lowered.startswith("дюйм"):
        return "дюйм"
    return UNITS.get(lowered, lowered)


def _number(raw: str) -> str:
    value = raw.replace(",", ".")
    return value.rstrip("0").rstrip(".") if "." in value else value


def extract_requirements(text: str) -> tuple[Requirement, ...]:
    found: dict[tuple[str, str], Requirement] = {}
    for match in FORMAT.finditer(text):
        value = f"A{match.group(1)}"
        found.setdefault(("format", value), Requirement("format", value, match.group(0).strip()))
    for match in MEASURE.finditer(text):
        unit = _unit(match.group(2))
        value = f"{_number(match.group(1))} {unit}"
        found.setdefault((unit, value), Requirement(unit, value, match.group(0).strip()))
    for match in GOST.finditer(text):
        value = f"ГОСТ {(match.group(1) or '').strip().upper()}{match.group(2)}".replace("  ", " ")
        found.setdefault(("gost", value), Requirement("gost", value, match.group(0).strip()))
    return tuple(found.values())


def check_requirements(
    requirements: Iterable[Requirement], texts: Iterable[str]
) -> tuple[RequirementCheck, ...]:
    offered: dict[str, list[str]] = {}
    for text in texts:
        for item in extract_requirements(text):
            values = offered.setdefault(item.key, [])
            if item.value not in values:
                values.append(item.value)
    checks: list[RequirementCheck] = []
    for requirement in requirements:
        values = offered.get(requirement.key, [])
        if requirement.value in values:
            checks.append(RequirementCheck(requirement, RequirementStatus.MET, requirement.value))
        elif values and requirement.key != "gost":
            checks.append(RequirementCheck(requirement, RequirementStatus.CONFLICT, values[0]))
        else:
            checks.append(RequirementCheck(requirement, RequirementStatus.UNKNOWN))
    return tuple(checks)
