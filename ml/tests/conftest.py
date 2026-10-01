import csv
from pathlib import Path

import pytest


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def synthetic_source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    notices, suppliers, products = [], [], []

    def lot(lot_id, day, text, codes, entrants, procedure=None):
        notices.append({
            "lot_id": lot_id, "procedure_id": procedure or lot_id, "publish_date": day,
            "procedure_name": text, "subject": text, "start_price": "10000.00",
            "customer_inn": "0000000099", "is_smp": "false", "is_eshop_or_aisgz": "ЭМ",
        })
        for inn, winner in entrants:
            suppliers.append({"lot_id": lot_id, "supplier_inn": inn, "supplier_kpp": "",
                              "is_winner": str(winner).lower()})
        for name, code in codes:
            products.append({"lot_id": lot_id, "product_name": name, "okpd2_code": code})

    first, second, new = "0000000001", "0000000002", "0000000003"
    lot("h1", "2024-01-10", "Обслуживание компьютеров", [("Компьютеры", "62.02.10")],
        [(first, True), (second, False)])
    lot("h2", "2024-05-10", "Бумага и пластик",
        [("Бумага", "17.23.11"), ("Пластик", "22.29.10")], [(first, True)])
    # Идентичные исходные строки не должны увеличивать историю участий.
    notices.append(notices[0].copy())
    suppliers.append(suppliers[0].copy())
    products.append(products[0].copy())
    for new_index, (prefix, day) in enumerate(
        [("train", "2024-08-10"), ("val", "2025-02-10"), ("test", "2025-08-10")], start=3
    ):
        new = f"{new_index:010d}"
        for i in range(4):
            lot(f"{prefix}{i}", day, "Обслуживание компьютеров",
                [("Компьютеры", "62.02.10")], [(first, i % 2 == 0), (second, i % 2 != 0)])
        lot(f"{prefix}_new", day, "Обслуживание компьютеров",
            [("Компьютеры", "62.02.10")], [(new, True)])
        lot(f"{prefix}_ambiguous", day, "Обслуживание компьютеров",
            [("Компьютеры", "62.02.10")], [(first, True), (second, True)])
        lot(f"{prefix}_conflict", day, "Обслуживание компьютеров",
            [("Компьютеры", "62.02.10")], [(first, True), (first, False), (second, False)])
        lot(f"{prefix}_missing", day, "Неизвестная закупка", [], [(first, True)])
    lot("future", "2026-06-01", "FUTURE_SECRET", [("FUTURE_SECRET", "99.99")], [(first, True)])
    # Один procedure_id на границе двух блоков не должен оказаться в разных целях.
    lot("cross1", "2024-12-20", "Граничная закупка", [("Компьютеры", "62.02")],
        [(first, True)], procedure="cross")
    lot("cross2", "2025-01-10", "Граничная закупка", [("Компьютеры", "62.02")],
        [(first, True)], procedure="cross")
    suppliers.append({"lot_id": "orphan", "supplier_inn": first, "supplier_kpp": "", "is_winner": "true"})
    write_csv(source / "Извещения_24-25.csv", list(notices[0]), notices)
    write_csv(source / "Поставщики_24-25.csv", list(suppliers[0]), suppliers)
    write_csv(source / "ТРУ_24-25.csv", list(products[0]), products)
    return source


@pytest.fixture
def prepared(synthetic_source, tmp_path):
    from rlt_ml.prepare import prepare

    config = Path(__file__).resolve().parents[1] / "configs/data.toml"
    out = tmp_path / "prepared"
    report = prepare(synthetic_source, out, config)
    return out, report
