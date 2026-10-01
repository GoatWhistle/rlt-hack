"""Generate a readable PDF of the ClickHouse table relationships."""

from pathlib import Path
from math import atan2, cos, sin

from reportlab.lib.colors import HexColor, Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


OUTPUT = Path(__file__).with_name("schema-relations.pdf")
WIDTH, HEIGHT = 1684, 1191  # A2 landscape, points


def font_path(*candidates):
    for candidate in candidates:
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("Нужен Arial или DejaVu Sans с поддержкой кириллицы")


pdfmetrics.registerFont(TTFont("Arial", font_path(
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)))
pdfmetrics.registerFont(TTFont("ArialBold", font_path(
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)))

INK = HexColor("#172238")
MUTED = HexColor("#5d6b80")
BLUE = HexColor("#2671a8")
ORANGE = HexColor("#c66a28")
GREEN = HexColor("#328663")
PURPLE = HexColor("#7856a6")
GRAY = HexColor("#697786")

# Coordinates are deliberately fixed so the PDF is stable and easy to review.
# Each table lists the identity and relationship columns, not every data field.
BOXES = {
    "suppliers": (55, 840, ["supplier_id  PK · UUID", "inn, kpps", "identity_status", "name, contacts, region"]),
    "sources": (455, 840, ["source_id  PK · UUID", "[1] supplier_id  → suppliers?", "source_type, base_url", "parser_name, options"]),
    "crawl_runs": (855, 840, ["run_id  ID · UUID", "[2] source_id  → sources", "started_at  часть ключа", "status, is_full_catalog"]),
    "observations": (1255, 840, ["observation_id  ID · UUID", "[4] run_id  → crawl_runs", "[3] source_id  → sources", "observed_at  часть ключа"]),
    "crawl_cursors": (455, 570, ["[5] source_id  → sources", "cursor_key  часть ключа", "[6] last_run_id  → crawl_runs?", "position, is_complete"]),
    "offers": (855, 570, ["offer_id  PK · UUID", "[7] source_id  → sources", "[8] supplier_id  → suppliers?", "[9] observation_id  → observations"]),
    "offer_matches": (1255, 570, ["[10] offer_id  PK → offers", "[11] catalog_item_id  → catalog_items?", "status, confidence", "offer_content_hash"]),
    "catalog_items": (1255, 300, ["catalog_item_id  PK · UUID", "[12] parent_id  → catalog_items?", "[13] merged_into_id  → catalog_items?", "name, status, okpd2_codes"]),
    "embeddings": (855, 300, ["entity_type + entity_id", "[18–20] → catalog_items | offers |", "               procurement_items", "model_key, dimensions"]),
    "lot_participations": (55, 60, ["[16] lot_id  → procurement_lots", "[17] supplier_id  → suppliers", "supplier_inn + supplier_kpp", "is_winner"]),
    "procurement_lots": (455, 60, ["lot_id  PK · String", "procedure_id, reqnum", "customer_inn, customer_kpp", "subject, start_price"]),
    "procurement_items": (855, 60, ["procurement_item_id  PK · UUID", "[14] lot_id  → procurement_lots", "[15] catalog_item_id  → catalog_items?", "product_name, okpd2_code"]),
}
BOX_W, BOX_H = 340, 175

# FK-like links. ClickHouse does not enforce any of these as foreign keys.
EDGES = [
    (1, "sources", "suppliers", "supplier_id", "supplier_id", "0..1", ORANGE),
    (2, "crawl_runs", "sources", "source_id", "source_id", "1", BLUE),
    (3, "observations", "sources", "source_id", "source_id", "1", BLUE),
    (4, "observations", "crawl_runs", "run_id", "run_id", "1", BLUE),
    (5, "crawl_cursors", "sources", "source_id", "source_id", "1", BLUE),
    (6, "crawl_cursors", "crawl_runs", "last_run_id", "run_id", "0..1*", BLUE),
    (7, "offers", "sources", "source_id", "source_id", "1", BLUE),
    (8, "offers", "suppliers", "supplier_id", "supplier_id", "0..1", ORANGE),
    (9, "offers", "observations", "observation_id", "observation_id", "1", BLUE),
    (10, "offer_matches", "offers", "offer_id", "offer_id", "1", GREEN),
    (11, "offer_matches", "catalog_items", "catalog_item_id", "catalog_item_id", "0..1", GREEN),
    (12, "catalog_items", "catalog_items", "parent_id", "catalog_item_id", "0..1", GREEN),
    (13, "catalog_items", "catalog_items", "merged_into_id", "catalog_item_id", "0..1", GREEN),
    (14, "procurement_items", "procurement_lots", "lot_id", "lot_id", "1", PURPLE),
    (15, "procurement_items", "catalog_items", "catalog_item_id", "catalog_item_id", "0..1", GREEN),
    (16, "lot_participations", "procurement_lots", "lot_id", "lot_id", "1", PURPLE),
    (17, "lot_participations", "suppliers", "supplier_id", "supplier_id", "1", ORANGE),
    (18, "embeddings", "catalog_items", "entity_id", "catalog_item_id", "type=catalog_item", GRAY),
    (19, "embeddings", "offers", "entity_id", "offer_id", "type=offer", GRAY),
    (20, "embeddings", "procurement_items", "entity_id", "procurement_item_id", "type=procurement_item", GRAY),
]


def label(c, x, y, value, size=13, color=INK, bold=False):
    c.setFillColor(color)
    c.setFont("ArialBold" if bold else "Arial", size)
    c.drawString(x, y, value)


def box(c, name, x, y, rows):
    c.setFillColor(HexColor("#ffffff"))
    c.setStrokeColor(HexColor("#cbd5e1"))
    c.roundRect(x, y, BOX_W, BOX_H, 12, fill=1, stroke=1)
    c.setFillColor(HexColor("#eaf1f7"))
    c.roundRect(x + 1, y + BOX_H - 43, BOX_W - 2, 42, 11, fill=1, stroke=0)
    label(c, x + 18, y + BOX_H - 28, name, 18, INK, True)
    for i, row in enumerate(rows):
        label(c, x + 18, y + BOX_H - 68 - i * 25, row, 13, MUTED)


def point(name, side, offset):
    x, y, _ = BOXES[name]
    if side == "left":
        return x, y + BOX_H / 2 + offset
    if side == "right":
        return x + BOX_W, y + BOX_H / 2 + offset
    if side == "top":
        return x + BOX_W / 2 + offset, y + BOX_H
    return x + BOX_W / 2 + offset, y


def endpoints(a, b, number):
    ax, ay, _ = BOXES[a]
    bx, by, _ = BOXES[b]
    dx, dy = bx - ax, by - ay
    # Spread links across the same edge of a box.
    offset = ((number * 3) % 7 - 3) * 12
    if abs(dx) >= abs(dy):
        sa, sb = ("right", "left") if dx > 0 else ("left", "right")
    else:
        sa, sb = ("top", "bottom") if dy > 0 else ("bottom", "top")
    return point(a, sa, offset), point(b, sb, -offset), sa, sb


def edge(c, number, source, target, color):
    if number == 3:
        start = (1425, 1015)
        end = (625, 1015)
        controls = ((1425, 1051), (625, 1051))
    elif number == 8:
        start = (1025, 745)
        end = (225, 840)
        controls = ((1025, 795), (225, 795))
    elif source == target:
        x, y, _ = BOXES[source]
        if number == 12:
            start, end = (x + BOX_W, y + 145), (x + BOX_W, y + 105)
            controls = ((x + BOX_W + 35, y + 145), (x + BOX_W + 35, y + 105))
        else:
            start, end = (x + BOX_W, y + 82), (x + BOX_W, y + 42)
            controls = ((x + BOX_W + 65, y + 82), (x + BOX_W + 65, y + 42))
    else:
        start, end, sa, sb = endpoints(source, target, number)
        span = min(145, max(65, abs(end[0] - start[0]) * 0.35, abs(end[1] - start[1]) * 0.35))
        directions = {"right": (1, 0), "left": (-1, 0), "top": (0, 1), "bottom": (0, -1)}
        va, vb = directions[sa], directions[sb]
        controls = ((start[0] + va[0] * span, start[1] + va[1] * span),
                    (end[0] + vb[0] * span, end[1] + vb[1] * span))
    c.setStrokeColor(Color(color.red, color.green, color.blue, alpha=0.72))
    c.setLineWidth(2.1)
    if number >= 18:
        c.setDash(5, 4)
    p = c.beginPath()
    p.moveTo(*start)
    p.curveTo(*controls[0], *controls[1], *end)
    c.drawPath(p)
    c.setDash()
    # Number at the source end identifies the exact fields on page two.
    t = 0.38 if number in (3, 6, 8, 12, 13) else 0.16
    px = (1-t)**3*start[0] + 3*(1-t)**2*t*controls[0][0] + 3*(1-t)*t*t*controls[1][0] + t**3*end[0]
    py = (1-t)**3*start[1] + 3*(1-t)**2*t*controls[0][1] + 3*(1-t)*t*t*controls[1][1] + t**3*end[1]
    c.setFillColor(color)
    c.circle(px, py, 11, fill=1, stroke=0)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("ArialBold", 10)
    c.drawCentredString(px, py - 3.5, str(number))
    angle = atan2(end[1] - controls[1][1], end[0] - controls[1][0])
    c.setFillColor(color)
    tip = c.beginPath()
    tip.moveTo(*end)
    for sign in (1, -1):
        tip.lineTo(end[0] - 12*cos(angle) + sign*5*sin(angle),
                   end[1] - 12*sin(angle) - sign*5*cos(angle))
    tip.close()
    c.drawPath(tip, fill=1, stroke=0)


def overview(c):
    label(c, 55, 1122, "Схема таблиц и связей · supplier_search", 30, INK, True)
    label(c, 55, 1087, "Актуальные миграции 0001–0002 · стрелка ведёт от поля-ссылки к записи назначения", 15, MUTED)
    for number, source, target, _, _, _, color in EDGES:
        edge(c, number, source, target, color)
    for name, (x, y, rows) in BOXES.items():
        box(c, name, x, y, rows)
    # The migrator's bookkeeping table is deliberately isolated.
    c.setFillColor(HexColor("#f2f5f8"))
    c.roundRect(1255, 75, 340, 118, 11, fill=1, stroke=0)
    label(c, 1273, 160, "schema_migrations", 17, INK, True)
    label(c, 1273, 133, "name  PK · String", 13, MUTED)
    label(c, 1273, 109, "checksum, statements, applied_at", 13, MUTED)
    label(c, 1273, 84, "Служебная таблица; связей нет", 12, MUTED)
    label(c, 55, 25, "Сплошная линия — логическая ссылка; пунктир — полиморфная. PK — логический ключ; ClickHouse не гарантирует уникальность и внешние ключи.", 13, MUTED)
    c.showPage()


def details(c):
    label(c, 55, 1122, "Расшифровка всех связей", 30, INK, True)
    label(c, 55, 1087, "Номера соответствуют линиям на первой странице. «0..1» означает необязательную ссылку.", 15, MUTED)
    x_positions = (58, 123, 552, 980, 1465)
    headers = ("№", "Таблица и поле", "Ссылается на", "Условие / кратность", "Тип")
    for x, header in zip(x_positions, headers):
        label(c, x, 1038, header, 14, INK, True)
    c.setStrokeColor(HexColor("#d6dee8"))
    c.line(55, 1027, 1625, 1027)
    for i, (number, source, target, field, target_field, cardinality, color) in enumerate(EDGES):
        y = 992 - i * 43
        if i % 2 == 0:
            c.setFillColor(HexColor("#f5f8fb"))
            c.rect(54, y - 13, 1571, 39, fill=1, stroke=0)
        label(c, x_positions[0], y, str(number), 13, color, True)
        label(c, x_positions[1], y, f"{source}.{field}", 13)
        label(c, x_positions[2], y, f"{target}.{target_field}", 13)
        label(c, x_positions[3], y, cardinality, 13, MUTED)
        label(c, x_positions[4], y, "полим." if number >= 18 else "логич.", 12, MUTED)
    label(c, 55, 100, "* crawl_cursors.last_run_id — UUID без Nullable; пока успешного обхода нет, приложение может хранить нулевой UUID.", 13, MUTED)
    label(c, 55, 74, "Связи контролирует приложение. UUID, совпавший с несуществующей записью, ClickHouse не отклоняет.", 13, MUTED)
    label(c, 55, 46, "Источники: context/clickhouse-schema.md; backend/migration/0001_initial_schema.sql; 0002_parsing_job.sql.", 12, MUTED)
    c.showPage()


def main():
    c = canvas.Canvas(str(OUTPUT), pagesize=(WIDTH, HEIGHT), pageCompression=1)
    c.setTitle("Схема таблиц и связей supplier_search")
    c.setAuthor("rlt-hack")
    overview(c)
    details(c)
    c.save()
    print(OUTPUT)


if __name__ == "__main__":
    main()
