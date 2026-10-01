import threading

from src.adapter.text.analyzer.analyzer import RussianAnalyzer, normalize, stem
from src.adapter.text.bm25.index import Bm25Index


def test_analyzer_normalises_drops_stopwords_and_stems() -> None:
    analyzer = RussianAnalyzer()
    assert analyzer.tokens("Ёлки, и ПАЛКИ: для дома!") == ("елки", "палки", "дома")
    assert analyzer.analyze("Крупы гречневые для школы") == ("круп", "гречнев", "школ")
    assert analyzer.analyze("Office papers A4") == ("offic", "paper", "a4")
    assert analyzer.analyze("в на и с") == ()
    assert normalize("ЁЖ") == "еж"
    assert stem("2026") == "2026"


def test_stemming_is_safe_across_threads() -> None:
    analyzer = RussianAnalyzer()
    results: list[tuple[str, ...]] = []

    def work() -> None:
        results.append(analyzer.analyze("молоко пастеризованное ультрапастеризованные"))

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(set(results)) == 1


def test_bm25_prefers_rare_and_repeated_terms() -> None:
    index = Bm25Index(
        (
            ("круп", "гречнев", "ядриц"),
            ("круп", "рис"),
            ("сахар",),
            (),
        )
    )
    scores = index.scores(("гречнев", "круп", "круп"))
    assert scores[0] > scores[1] > 0
    assert scores[2] == scores[3] == 0
    assert index.scores(("нет",)) == [0.0, 0.0, 0.0, 0.0]
    assert len(index) == 4
    assert index.idf("гречнев") > index.idf("круп")


def test_bm25_handles_empty_documents() -> None:
    assert Bm25Index(((), ())).scores(("x",)) == [0.0, 0.0]
