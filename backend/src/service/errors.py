"""Ошибки слоя бизнес-логики.

Сбои обхода объявляются в слое адаптеров: сервис их не классифицирует, а
фиксирует в журнале как неудачный обход источника.
"""


class ServiceError(Exception):
    """Базовая ошибка бизнес-логики."""


class ProviderNotConfiguredError(ServiceError):
    """Ни один адаптер источника не включён: обходить нечего."""


class RegistryNotConfiguredError(ServiceError):
    """Путь к выгрузке реестра МСП не задан."""


class EmptyRegistryDumpError(ServiceError):
    """Выгрузка реестра МСП прочитана, но компаний в ней нет."""
