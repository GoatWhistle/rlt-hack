"""Ошибки слоя бизнес-логики.

Сбои обхода объявляются в слое адаптеров: сервис их не классифицирует, а
фиксирует в журнале как неудачный обход источника.
"""


class ServiceError(Exception):
    """Базовая ошибка бизнес-логики."""


class ProviderNotConfiguredError(ServiceError):
    """Ни один адаптер источника не включён: обходить нечего."""


class SearchError(ServiceError):
    pass


class UninterpretableQueryError(SearchError):
    def __init__(self) -> None:
        super().__init__("no searchable items in the text")


class SearchUnavailableError(SearchError):
    def __init__(self, channels: tuple[str, ...]) -> None:
        super().__init__(f"every retrieval channel failed: {', '.join(channels)}")
        self.channels = channels


class SearchTimeoutError(SearchError):
    def __init__(self, seconds: float) -> None:
        super().__init__(f"search took longer than {seconds} seconds")
        self.seconds = seconds


class SearchNotFoundError(SearchError):
    def __init__(self, search_id: object) -> None:
        super().__init__(f"search {search_id} not found")
        self.search_id = search_id


class StorageUnavailableError(ServiceError):
    def __init__(self) -> None:
        super().__init__("storage is temporarily unavailable")


class SupplierNotFoundError(ServiceError):
    def __init__(self, supplier_id: object) -> None:
        super().__init__(f"supplier {supplier_id} not found")
        self.supplier_id = supplier_id


class UploadError(ServiceError):
    pass


class UploadNotFoundError(UploadError):
    def __init__(self, upload_id: object) -> None:
        super().__init__(f"upload {upload_id} not found")
        self.upload_id = upload_id


class UploadQueueFullError(UploadError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"more than {limit} lots are waiting for processing, retry later")
        self.limit = limit


class LotNotFoundError(UploadError):
    def __init__(self, upload_id: object, lot_id: str) -> None:
        super().__init__(f"lot {lot_id} not found in upload {upload_id}")
        self.upload_id = upload_id
        self.lot_id = lot_id
