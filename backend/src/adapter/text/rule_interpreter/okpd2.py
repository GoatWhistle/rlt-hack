import re

OKPD2 = re.compile(
    r"(?:(?<=\s)|^)(?:окпд\s*2?\s*[:№]?\s*)?(?P<code>\d{2}\.\d{2}(?:\.\d{1,3}){0,3})(?![\d.])",
    re.IGNORECASE,
)


def extract_okpd2(text: str) -> tuple[str, str]:
    codes = [match.group("code") for match in OKPD2.finditer(text)]
    if not codes:
        return "", text
    return codes[0], OKPD2.sub(" ", text)
