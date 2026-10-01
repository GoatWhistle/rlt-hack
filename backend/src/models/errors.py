class DomainError(ValueError):
    pass


class InvalidInputError(DomainError):
    pass


class EmptySearchTextError(InvalidInputError):
    def __init__(self) -> None:
        super().__init__("search text is empty")


class SearchTextTooLongError(InvalidInputError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"search text is longer than {limit} characters")
        self.limit = limit


class InvalidCandidateLimitError(InvalidInputError):
    def __init__(self, minimum: int, maximum: int) -> None:
        super().__init__(f"candidate limit must be within {minimum}..{maximum}")
        self.minimum = minimum
        self.maximum = maximum


class InvalidQuantityError(DomainError):
    def __init__(self) -> None:
        super().__init__("quantity must be positive and have a unit")


class InvalidQueryItemError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"query item is invalid: {reason}")


class InvalidSearchRequestError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"search request is invalid: {reason}")


class InvalidEvidenceError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"evidence is invalid: {reason}")


class InvalidScoreError(DomainError):
    def __init__(self, value: float) -> None:
        super().__init__(f"score must be a finite number within 0..1, got {value}")


class InvalidRankError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"rank is invalid: {reason}")


class InvalidMatchError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"product match is invalid: {reason}")


class InvalidCandidateError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"candidate is invalid: {reason}")


class InvalidPurchaseSummaryError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"purchase summary is invalid: {reason}")


class InvalidSearchResultError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"search result is invalid: {reason}")


class InvalidProcurementLotError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"procurement lot is invalid: {reason}")


class InvalidUploadError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"upload is invalid: {reason}")


class InvalidLotResultError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"lot result is invalid: {reason}")


class NoticeFileError(InvalidInputError):
    pass


class UnreadableNoticeFileError(NoticeFileError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"the file cannot be read as a notice table: {reason}")


class MissingNoticeColumnsError(NoticeFileError):
    def __init__(self, columns: tuple[str, ...]) -> None:
        super().__init__(f"required columns are missing: {', '.join(columns)}")
        self.columns = columns


class TooManyNoticeRowsError(NoticeFileError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"the file has more than {limit} rows")
        self.limit = limit


class NoValidLotsError(NoticeFileError):
    def __init__(self) -> None:
        super().__init__("no row of the file is a valid procurement lot")


class UnsupportedNoticeFormatError(NoticeFileError):
    def __init__(self) -> None:
        super().__init__("only CSV notice tables are supported")
