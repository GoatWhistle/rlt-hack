from contextlib import AbstractContextManager, nullcontext


class UntimedStages:
    def stage(self, name: str) -> AbstractContextManager[None]:
        return nullcontext()
