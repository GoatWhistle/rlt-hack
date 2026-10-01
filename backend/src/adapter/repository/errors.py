"""Ошибки адаптеров баз данных."""


class RepositoryError(Exception):
    """Базовая ошибка работы с хранилищем."""


class RepositoryUnavailableError(RepositoryError):
    """Хранилище недоступно: соединение не установлено или запрос отклонён."""


class MigrationError(RepositoryError):
    """Миграция не применена: файл некорректен или запрос завершился ошибкой."""
