from dataclasses import dataclass

from src.models.enums import ComponentState


@dataclass(frozen=True, slots=True)
class ComponentHealth:
    name: str
    state: ComponentState
    required: bool = True


@dataclass(frozen=True, slots=True)
class Readiness:
    components: tuple[ComponentHealth, ...]

    @property
    def ready(self) -> bool:
        return all(item.state == ComponentState.UP for item in self.components if item.required)

    @property
    def degraded(self) -> tuple[str, ...]:
        return tuple(
            item.name
            for item in self.components
            if not item.required and item.state != ComponentState.UP
        )
