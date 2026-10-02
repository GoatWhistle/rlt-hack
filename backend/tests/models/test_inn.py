import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.models.company.inn import WEIGHTS_10, WEIGHTS_11, WEIGHTS_12, is_valid_inn, normalize_inn
from tests.fakes.domain import make_supplier


def check_digit(digits: str, weights: tuple[int, ...]) -> str:
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=False))
    return str(total % 11 % 10)


def company_inn(body: str) -> str:
    return body + check_digit(body, WEIGHTS_10)


def person_inn(body: str) -> str:
    eleven = body + check_digit(body, WEIGHTS_11)
    return eleven + check_digit(eleven, WEIGHTS_12)


BODIES_9 = st.text("0123456789", min_size=9, max_size=9)
BODIES_10 = st.text("0123456789", min_size=10, max_size=10)


@given(BODIES_9)
def test_company_inn_with_its_check_digit_is_valid(body: str) -> None:
    value = company_inn(body)
    assert is_valid_inn(value) == (len(set(value)) > 1)


@given(BODIES_10)
def test_person_inn_with_its_check_digits_is_valid(body: str) -> None:
    value = person_inn(body)
    assert is_valid_inn(value) == (len(set(value)) > 1)


@given(BODIES_9, st.integers(1, 9))
def test_a_wrong_check_digit_is_rejected(body: str, shift: int) -> None:
    valid = company_inn(body)
    broken = valid[:9] + str((int(valid[9]) + shift) % 10)
    assert not is_valid_inn(broken)


@given(st.text(max_size=20))
def test_normalized_inn_is_always_valid(raw: str) -> None:
    normalized = normalize_inn(raw)
    assert normalized is None or is_valid_inn(normalized)


@pytest.mark.parametrize("value", ["0000000000", "111111111111", "７８０１２３４５６４", ""])
def test_placeholders_and_foreign_digits_are_rejected(value: str) -> None:
    assert not is_valid_inn(value)


def test_inn_loses_its_leading_zero_in_numeric_exports() -> None:
    value = company_inn("012345678")
    assert normalize_inn(value[1:]) == value
    assert normalize_inn(f"ИНН {value}") == value


@pytest.mark.parametrize(("inn", "valid"), [("7801234564", True), ("7801234567", False)])
def test_supplier_uses_the_same_rule(inn: str, valid: bool) -> None:
    assert make_supplier(inn=inn).has_valid_inn is valid
    assert not make_supplier(inn=None).has_valid_inn
