"""Правило роли компании по сведениям реестра МСП.

Заявленная в реестре собственная продукция — прямое указание на производство,
поэтому она важнее ОКВЭД. Иначе роль даёт основной ОКВЭД по справочнику (из
сведений реестра, а если там его нет — из отчётности, что видно в основании):
дополнительные коды перечисляют всё, чем компания вправе заниматься, и о
реальной деятельности говорят мало. Без совпадения роль остаётся неизвестной.
"""

from src.models.company.registry import MspCompany
from src.models.enums import SupplierRole
from src.service.registry.protocols import OkvedRoles


def role_of(company: MspCompany, roles: OkvedRoles) -> tuple[SupplierRole, str]:
    source = f"реестр МСП ФНС на {company.registry_date:%d.%m.%Y}"
    if company.products:
        return (
            SupplierRole.MANUFACTURER,
            f"Заявляет собственную продукцию, ОКПД2 {company.products[0]} ({source})",
        )
    if not company.okved_main:
        return SupplierRole.UNKNOWN, ""
    role = roles.role_by_okved(company.okved_main)
    if role is None:
        return SupplierRole.UNKNOWN, ""
    title = f" «{company.okved_main_name}»" if company.okved_main_name else ""
    kind = "Основной ОКВЭД по отчётности" if company.okved_main_reported else "Основной ОКВЭД"
    return role, f"{kind} {company.okved_main}{title} ({source})"
