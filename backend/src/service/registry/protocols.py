"""Интерфейсы, которые потребляет обогащение компаний по реестру МСП."""

from collections.abc import AsyncIterator, Sequence
from datetime import date
from typing import Protocol

from src.models.enums import SupplierRole
from src.models.registry import MspCompany


class CompanyRegistry(Protocol):
    async def find(self, inns: Sequence[str]) -> dict[str, MspCompany]:
        """Сведения реестра по ИНН; компаний вне реестра в ответе нет."""


class OkvedRoles(Protocol):
    """Справочник ролей: какой роли соответствует код ОКВЭД."""

    @property
    def version(self) -> str: ...

    def role_by_okved(self, code: str) -> SupplierRole | None: ...


class RegistryDump(Protocol):
    def read(self) -> AsyncIterator[Sequence[MspCompany]]:
        """Отдаёт компании выгрузки пачками; повреждённая выгрузка — исключение."""


class RegistryStore(Protocol):
    async def save_many(self, companies: Sequence[MspCompany]) -> None: ...

    async def remove_older(self, registry_date: date) -> None:
        """Удаляет сведения выгрузок старше указанной даты."""
