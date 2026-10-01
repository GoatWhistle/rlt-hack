"""Обогащение компаний пакета сведениями реестра МСП.

Вызывается сразу после обхода источника и до нормализации. Роль проставляется
только компаниям, у которых её ещё нет, а коды ОКВЭД — только тем, у кого их
не дал источник: обогащение дополняет данные источника и не спорит с ними.
Компании без ИНН и вне реестра проходят без изменений.
"""

import dataclasses
import logging

from src.models.enums import SupplierRole
from src.models.package import SupplierPackage
from src.models.registry import MspCompany
from src.models.supplier import Supplier
from src.service.registry.protocols import CompanyRegistry, OkvedRoles
from src.service.registry.roles import role_of

logger = logging.getLogger(__name__)


class SupplierRegistryEnricher:
    def __init__(self, registry: CompanyRegistry, roles: OkvedRoles) -> None:
        self._registry = registry
        self._roles = roles

    async def enrich(self, package: SupplierPackage) -> SupplierPackage:
        inns = sorted({supplier.inn for supplier in package.suppliers if supplier.inn})
        if not inns:
            return package
        found = await self._registry.find(inns)
        suppliers = tuple(
            self._apply(supplier, found.get(supplier.inn or "")) for supplier in package.suppliers
        )
        logger.info(
            "Источник %s: компаний с ИНН — %d, найдено в реестре МСП — %d, с ролью — %d",
            package.source.provider_name,
            len(inns),
            len(found),
            sum(supplier.role != SupplierRole.UNKNOWN for supplier in suppliers),
        )
        return dataclasses.replace(package, suppliers=suppliers)

    def _apply(self, supplier: Supplier, company: MspCompany | None) -> Supplier:
        if company is None:
            return supplier
        changes: dict[str, object] = {}
        if not supplier.okved_codes:
            codes = (company.okved_main, *company.okved_extra)
            changes["okved_codes"] = tuple(dict.fromkeys(code for code in codes if code))
        if supplier.role == SupplierRole.UNKNOWN:
            role, evidence = role_of(company, self._roles)
            if role != SupplierRole.UNKNOWN:
                changes["role"] = role
                changes["role_evidence"] = evidence
        return dataclasses.replace(supplier, **changes) if changes else supplier
