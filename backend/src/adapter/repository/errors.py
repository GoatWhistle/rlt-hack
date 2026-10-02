"""Ошибки адаптеров баз данных."""


class RepositoryError(Exception):
    """Базовая ошибка работы с хранилищем."""


class RepositoryUnavailableError(RepositoryError):
    """Хранилище недоступно: соединение не установлено или запрос отклонён."""


class MigrationError(RepositoryError):
    """Миграция не применена: файл некорректен или запрос завершился ошибкой."""


class ReferenceDataError(RepositoryError):
    """Файл справочника отсутствует или описан неверно."""


class CorruptRecordError(RepositoryError):
    def __init__(self, record: str, reason: str) -> None:
        super().__init__(f"stored {record} cannot be read: {reason}")
        self.record = record
        self.reason = reason


class DatasetMissingError(RepositoryError):
    def __init__(self, dataset: str) -> None:
        super().__init__(f"dataset {dataset} is not loaded")
        self.dataset = dataset
