from collections import defaultdict
from collections.abc import Mapping

type Labels = tuple[tuple[str, str], ...]

COUNTER_SUFFIX = "_total"
ESCAPES = str.maketrans({"\\": "\\\\", '"': '\\"', "\n": "\\n"})


def _labels(labels: Mapping[str, str] | None) -> Labels:
    return tuple(sorted((labels or {}).items()))


def _rendered(labels: Labels) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{name}="{value.translate(ESCAPES)}"' for name, value in labels)
    return "{" + inner + "}"


class Metrics:
    def __init__(self) -> None:
        self._series: defaultdict[str, defaultdict[Labels, float]] = defaultdict(
            lambda: defaultdict(float)
        )

    def count(
        self, name: str, labels: Mapping[str, str] | None = None, amount: float = 1.0
    ) -> None:
        self._series[name][_labels(labels)] += amount

    def value(self, name: str, labels: Mapping[str, str] | None = None) -> float:
        series = self._series.get(name)
        return 0.0 if series is None else series.get(_labels(labels), 0.0)

    def render(self) -> str:
        lines: list[str] = []
        for name in sorted(self._series):
            if name.endswith(COUNTER_SUFFIX):
                lines.append(f"# TYPE {name} counter")
            lines.extend(
                f"{name}{_rendered(labels)} {value:g}"
                for labels, value in sorted(self._series[name].items())
            )
        return "\n".join(lines) + "\n"
