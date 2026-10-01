"""Разбор XML выгрузки реестра МСП ФНС: один элемент «Документ» на компанию.

Формат открытых данных ФНС (7707329152-rsmp): реквизиты юрлица в «ОргВклМСП»,
предпринимателя — в «ИПВклМСП», виды деятельности в «СвОКВЭД», заявленная
продукция в «СвПрод». У части компаний основного кода в «СвОКВЭД» нет, и он
есть только в «СвОКВЭДотч» — видах деятельности по данным отчётности. Разбор
потоковый: прочитанные элементы сразу удаляются, поэтому файл любого размера
не держится в памяти целиком.
"""

import re
from datetime import date, datetime
from typing import IO, Any

from lxml import etree

from src.models.registry import MspCompany

_INN = re.compile(r"^(\d{10}|\d{12})$")


def parse_stream(stream: IO[bytes]) -> list[MspCompany]:
    companies = []
    for _, element in etree.iterparse(stream, tag="Документ", huge_tree=True):
        company = parse_document(element)
        if company is not None:
            companies.append(company)
        element.clear()
        while element.getprevious() is not None:
            del element.getparent()[0]
    return companies


def parse_document(element: Any) -> MspCompany | None:
    """Документ без ИНН или даты сведений пропускается: сопоставить его не с чем."""
    registry_date = _date(element.get("ДатаСост"))
    organization = element.find("ОргВклМСП")
    entrepreneur = element.find("ИПВклМСП")
    if organization is not None:
        inn = organization.get("ИННЮЛ") or ""
        name = organization.get("НаимОргСокр") or organization.get("НаимОрг") or ""
    elif entrepreneur is not None:
        inn = entrepreneur.get("ИННФЛ") or ""
        name = _entrepreneur_name(entrepreneur.find("ФИОИП"))
    else:
        return None
    inn = inn.strip()
    if registry_date is None or not _INN.match(inn):
        return None
    main = element.find("СвОКВЭД/СвОКВЭДОсн")
    reported = main is None
    if reported:
        main = element.find("СвОКВЭДотч/СвОКВЭДОсн")
    return MspCompany(
        inn=inn,
        name=" ".join(name.split()),
        registry_date=registry_date,
        okved_main=_attribute(main, "КодОКВЭД"),
        okved_main_name=_attribute(main, "НаимОКВЭД"),
        okved_main_reported=reported and main is not None,
        okved_extra=_codes(element.findall("СвОКВЭД/СвОКВЭДДоп"), "КодОКВЭД"),
        products=_codes(element.findall("СвПрод"), "КодПрод"),
    )


def _entrepreneur_name(fio: Any) -> str:
    if fio is None:
        return ""
    parts = [fio.get(key) for key in ("Фамилия", "Имя", "Отчество")]
    return "ИП " + " ".join(part for part in parts if part)


def _attribute(element: Any, name: str) -> str:
    return (element.get(name) or "").strip() if element is not None else ""


def _codes(elements: list[Any], name: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(code for element in elements if (code := _attribute(element, name))))


def _date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None
