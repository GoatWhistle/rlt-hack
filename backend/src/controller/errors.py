class RequestFileError(Exception):
    pass


class MissingFileError(RequestFileError):
    def __init__(self) -> None:
        super().__init__("multipart field 'file' is required")


class FileTooLargeError(RequestFileError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"the file is larger than {limit} bytes")
        self.limit = limit


class UnsupportedFileTypeError(RequestFileError):
    def __init__(self, allowed: tuple[str, ...]) -> None:
        super().__init__(f"only {', '.join(allowed)} files are accepted")
        self.allowed = allowed


class SearchBusyError(Exception):
    def __init__(self, limit: int) -> None:
        super().__init__(f"{limit} searches are already running, retry later")
        self.limit = limit
