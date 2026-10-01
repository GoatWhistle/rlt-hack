"""Правила идентичности предложения как зависимость сервиса.

Сами правила живут в `identity`: ими пользуются и адаптеры источников при
обходе, и перевод сохранённых позиций на новое правило. Обёртка нужна, чтобы
сервис зависел от интерфейса, а не от модуля адаптеров.
"""

from uuid import UUID

from src.adapter.supplier import identity


class OfferIdentityRules:
    def rekey(self, previous: str, url: str, name: str) -> str:
        return identity.rekey(previous, url, name)

    def offer_id(self, source_id: UUID, external_id: str) -> UUID:
        return identity.offer_id(source_id, external_id)
