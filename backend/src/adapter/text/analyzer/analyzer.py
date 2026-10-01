import os
import re
import threading
from functools import lru_cache

import snowballstemmer

from src.adapter.text.analyzer.stopwords import ENGLISH_STOPWORDS, RUSSIAN_STOPWORDS

TOKEN = re.compile(r"[0-9a-zа-я]+")
CYRILLIC = re.compile(r"[а-я]")
LATIN = re.compile(r"[a-z]")
STOPWORDS = RUSSIAN_STOPWORDS | ENGLISH_STOPWORDS
MIN_TOKEN_LENGTH = 2

_local = threading.local()


def normalize(text: str) -> str:
    return text.lower().replace("ё", "е")


def _stemmer(language: str) -> snowballstemmer.stemmer:
    stemmers: dict[str, snowballstemmer.stemmer] | None = getattr(_local, "stemmers", None)
    if stemmers is None:
        stemmers = {}
        _local.stemmers = stemmers
    if language not in stemmers:
        stemmers[language] = snowballstemmer.stemmer(language)
    return stemmers[language]


@lru_cache(maxsize=200_000)
def stem(token: str) -> str:
    if CYRILLIC.search(token):
        return str(_stemmer("russian").stemWord(token))
    if LATIN.search(token):
        return str(_stemmer("english").stemWord(token))
    return token


class RussianAnalyzer:
    def tokens(self, text: str) -> tuple[str, ...]:
        return tuple(
            token
            for token in TOKEN.findall(normalize(text))
            if len(token) >= MIN_TOKEN_LENGTH and token not in STOPWORDS
        )

    def analyze(self, text: str) -> tuple[str, ...]:
        return tuple(stem(token) for token in self.tokens(text))

    def prefixes(self, text: str) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(os.path.commonprefix([token, stem(token)]) for token in self.tokens(text))
        )
