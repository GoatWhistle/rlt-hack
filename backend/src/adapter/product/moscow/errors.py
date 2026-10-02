"""Ошибки чтения каталога СТЕ."""


class MoscowProductError(Exception):
    pass


class MoscowProductFormatError(MoscowProductError):
    pass


class MoscowProductIncompleteError(MoscowProductError):
    pass
