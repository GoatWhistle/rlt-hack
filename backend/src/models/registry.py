"""Запись единого реестра субъектов МСП ФНС о компании."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class MspCompany:
    inn: str
    name: str
    # Дата, на которую ФНС сформировала сведения: по ней видно, насколько они свежие.
    registry_date: date
    okved_main: str = ""
    okved_main_name: str = ""
    # Основной ОКВЭД взят из сведений отчётности: в реестре у компании его нет.
    okved_main_reported: bool = False
    okved_extra: tuple[str, ...] = ()
    # Коды ОКПД2 продукции, которую компания заявила как собственную.
    products: tuple[str, ...] = ()
