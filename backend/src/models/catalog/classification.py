"""Классификация позиции: код ОКПД2, рубрика и тип с указанием происхождения.

Классификатор не угадывает: если ни один канал не дал кода, запись остаётся без
него, а метод показывает, какой канал сработал и что именно послужило
основанием.
"""

from dataclasses import dataclass

from src.models.enums import ClassificationMethod, ItemType


@dataclass(frozen=True, slots=True)
class Classification:
    okpd2_code: str = ""
    okpd2_name: str = ""
    # Число значащих цифр: 2 — класс, 4 — группа, 6 — подгруппа, 9 — полный код.
    okpd2_level: int = 0
    rubric_code: str = ""
    rubric_name: str = ""
    item_type: ItemType = ItemType.UNKNOWN
    method: ClassificationMethod = ClassificationMethod.NONE
    confidence: float = 0.0
    # Что сработало: совпавшее название, раздел каталога или слово словаря.
    evidence: str = ""
    algorithm_version: str = ""
