import re

from src.adapter.text.rule_interpreter.quantity import QUANTITY

HARD_BREAK = re.compile(r"\s*[;\n•·▪●]\s*")
NUMBERED_MARKER = re.compile(r"(?:^|\s)\d{1,2}[.)]\s+(?=[^\W\d_])")
DASH_MARKER = re.compile(r"(?:^|\s)[-–—*]\s+(?=\w)")
DASHED_LIST = re.compile(r"^\s*[-–—*]\s")
QUANTITY_JOINT = re.compile(r"\s*(?:,|\s+и\s+)\s*", re.IGNORECASE)


def _split_after_quantities(chunk: str) -> list[str]:
    pieces: list[str] = []
    start = 0
    for match in QUANTITY.finditer(chunk):
        joint = QUANTITY_JOINT.match(chunk, match.end())
        if joint is None or joint.end() >= len(chunk):
            continue
        pieces.append(chunk[start : match.end()])
        start = joint.end()
    pieces.append(chunk[start:])
    return pieces


def split_positions(text: str) -> list[str]:
    chunks = HARD_BREAK.split(text)
    chunks = [part for chunk in chunks for part in NUMBERED_MARKER.split(chunk)]
    if DASHED_LIST.match(text):
        chunks = [part for chunk in chunks for part in DASH_MARKER.split(chunk)]
    pieces = [piece for chunk in chunks for piece in _split_after_quantities(chunk)]
    return [piece.strip() for piece in pieces if piece.strip()]
