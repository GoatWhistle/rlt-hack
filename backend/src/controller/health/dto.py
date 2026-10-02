from typing import Literal

from src.controller.http.schema import CamelModel
from src.models.enums import ComponentState
from src.models.health import Readiness


class LiveDto(CamelModel):
    status: Literal["ok"] = "ok"


class ComponentDto(CamelModel):
    name: str
    state: ComponentState
    required: bool


class ReadinessDto(CamelModel):
    ready: bool
    degraded: list[str]
    components: list[ComponentDto]

    @classmethod
    def of(cls, readiness: Readiness) -> "ReadinessDto":
        return cls(
            ready=readiness.ready,
            degraded=list(readiness.degraded),
            components=[
                ComponentDto(
                    name=component.name, state=component.state, required=component.required
                )
                for component in readiness.components
            ],
        )
