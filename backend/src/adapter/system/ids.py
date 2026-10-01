from uuid import UUID, uuid4


class Uuid4Generator:
    def new(self) -> UUID:
        return uuid4()
