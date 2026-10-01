"""Назначение версии строки для ReplacingMergeTree.

Версия строго возрастает для одного ключа ORDER BY. Времени now() недостаточно:
два обновления могут получить одинаковую отметку, поэтому счётчик состояния
основан на микросекундах UTC и дополнительно монотонен внутри процесса.

Ограничение: порядок версий между процессами опирается на часы узлов. Внутри
одного процесса источники обходятся конкурентно и делят один счётчик, поэтому
их записи упорядочены между собой.
"""

import threading
from datetime import datetime


def event_version(moment: datetime) -> int:
    """Версия журнальной записи: детерминирована по её собственному времени.

    Повторная доставка того же наблюдения или обхода даёт ту же версию
    и то же содержимое, поэтому дубль не создаёт новой версии.
    """
    version = int(moment.timestamp() * 1_000_000)
    if version <= 0:
        raise ValueError("время записи должно быть позже начала эпохи")
    return version


class VersionSequencer:
    """Монотонные версии для таблиц состояния."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last = 0

    def next(self) -> int:
        now = int(datetime.now().timestamp() * 1_000_000)
        with self._lock:
            self._last = max(now, self._last + 1)
            return self._last
