from typing import Literal

from src.controller.http.response.schema import CamelModel
from src.models.enums import ComponentState
from src.models.operations.health import Readiness


class LiveDto(CamelModel):
    status: Literal["ok"] = "ok"


class ComponentDto(CamelModel):
    name: str
    state: ComponentState


class ReadinessDto(CamelModel):
    ready: bool
    components: list[ComponentDto]

    @classmethod
    def of(cls, readiness: Readiness) -> "ReadinessDto":
        return cls(
            ready=readiness.ready,
            components=[
                ComponentDto(name=component.name, state=component.state)
                for component in readiness.components
            ],
        )
