"""Источник данных: каталог, сайт, фид, прайс, реестр или датасет."""

from dataclasses import dataclass
from uuid import UUID

from src.models.enums import SourceType, VerificationStatus


@dataclass(frozen=True, slots=True)
class Source:
    """Паспорт источника. Объявляется адаптером: параметров обхода в нём нет.

    Адреса, селекторы и лимиты принадлежат адаптеру источника, поэтому здесь
    остаются только сведения, которые нужны данным: кто источник, кому он
    принадлежит и каким адаптером прочитан.
    """

    source_id: UUID
    name: str
    base_url: str
    source_type: SourceType
    # Имя адаптера, который читает источник: оно же пишется в журнал обхода.
    provider_name: str
    # NULL у общего каталога: он представляет многих продавцов.
    supplier_id: UUID | None = None
    ownership_status: VerificationStatus = VerificationStatus.UNVERIFIED
    ownership_evidence_url: str = ""
