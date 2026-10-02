from collections.abc import Iterator
from contextlib import contextmanager

from src.controller.errors import SearchBusyError


class Admission:
    def __init__(self, limit: int) -> None:
        if limit < 1:
            raise ValueError(limit)
        self._limit = limit
        self._active = 0

    @property
    def active(self) -> int:
        return self._active

    @contextmanager
    def slot(self) -> Iterator[None]:
        if self._active >= self._limit:
            raise SearchBusyError(self._limit)
        self._active += 1
        try:
            yield
        finally:
            self._active -= 1
