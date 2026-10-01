"""Перенос кода из архива закупок: соединение по нормализованному названию.

Это не предсказание, а джойн: код берётся у позиции архива, которую заказчик
уже классифицировал сам. Индекс строится один раз на запуск и живёт в памяти —
по названиям нельзя спрашивать хранилище по одному, их тысячи.
"""

import logging
from collections.abc import Callable, Iterable

logger = logging.getLogger(__name__)


def build_index(
    items: Iterable[tuple[str, str]],
    core_name: Callable[[str], str],
) -> dict[str, str]:
    """Название приводится тем же нормализатором, что и предложения.

    Одно название с разными кодами — разметка архива противоречива, поэтому
    такая запись из индекса убирается: лучше не дать кода, чем дать неверный.
    """
    codes: dict[str, set[str]] = {}
    for name, code in items:
        key = core_name(name)
        if not key or not code:
            continue
        codes.setdefault(key, set()).add(code)
    index = {key: next(iter(values)) for key, values in codes.items() if len(values) == 1}
    dropped = len(codes) - len(index)
    if dropped:
        logger.info("Индекс архива: названий с противоречивым кодом — %d", dropped)
    return index
