import re

from src.models.supplier import Supplier

INN_PATTERN = re.compile(r"\d{10}|\d{12}")


def has_valid_inn(supplier: Supplier) -> bool:
    return supplier.inn is not None and INN_PATTERN.fullmatch(supplier.inn) is not None
