class FileAdapterError(ValueError):
    pass


class MissingInnColumnError(FileAdapterError):
    def __init__(self, name: str, column: str) -> None:
        super().__init__(f"{name}: column {column} is missing")
        self.column = column
