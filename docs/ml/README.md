# ML и качество рекомендаций

## ML-пайплайн

Датасет обрабатывается на сервере данных в `/root/rlt`; ZIP и производные таблицы не переносите на рабочий компьютер. Для окружения ML нужен Python 3.12. Все пути ниже показаны для сервера данных, кроме команды оценки на GPU.

```bash
cd /root/rlt/work/ml
python3.12 -m venv /root/rlt/.venv312
/root/rlt/.venv312/bin/pip install -e '.[dev]'
/root/rlt/.venv312/bin/pytest
/root/rlt/.venv312/bin/rlt-prepare \
  --source '/root/rlt/Данные 24-25.zip' \
  --out /root/rlt/ready-v1 \
  --config configs/data.toml
```

Для baseline запустите `rlt-evaluate-retrieval --data /root/rlt/ready-v1 --out /root/rlt/runs/bm25-validation --split validation --model bm25 --config configs/compare_qwen.toml` на подготовленных валидационных данных. На GPU заранее закешируйте открытые веса командой `rlt-cache-models --model Qwen/Qwen3-Embedding-0.6B --model Qwen/Qwen3-Embedding-4B --manifest /root/rlt/runs/models.json`. После этого оценка может идти без сети, задайте `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`.

Две сравниваемые модели и общая выборка задаются в `configs/compare_qwen.toml`; для каждого процесса нужен свой `--out`, модели должны видеть один набор `validation` файлов. После передачи производных validation таблиц на GPU перейдите в `/root/rlt/work/ml` и запустите команды в отдельных терминалах:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 rlt-evaluate-retrieval \
  --data /root/rlt/data/ready-v1 --out /root/rlt/runs/qwen-06b \
  --split validation --model Qwen/Qwen3-Embedding-0.6B --hybrid \
  --config configs/compare_qwen.toml --batch-size 4 \
  --gpu-memory-fraction 0.29 --cpu-threads 2

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 rlt-evaluate-retrieval \
  --data /root/rlt/data/ready-v1 --out /root/rlt/runs/qwen-4b \
  --split validation --model Qwen/Qwen3-Embedding-4B --hybrid \
  --config configs/compare_qwen.toml --batch-size 1 \
  --gpu-memory-fraction 0.68 --cpu-threads 2
```

В текущем сравнении выбран Qwen3-Embedding-4B BF16 + BM25/RRF. Отдельный Qwen3-Embedding-8B NF4 прогон был остановлен до завершения индекса; качество не измерялось, поэтому 8B не входит в рабочий pipeline. Зафиксированный частичный запуск указан в [журнале экспериментов](experiments.md).

GPU-проверка запускается через `rlt-gpu-check`. Замеры качества и ресурсов, ограничения метрик и фактические результаты ведутся в [журнале экспериментов](experiments.md).

Для оценки CatBoost поверх готового retrieval-пула используйте только validation
прогнозы и модель, обученную на train. Команда строит признаки по validation-ТРУ
и считает метрики с пропуском победителя, если его нет в пуле; это oracle-режим
для upstream предсказания ТРУ:

```bash
cd /root/rlt/work/ml
PYTHONPATH=src /root/rlt/.venv312/bin/python -m rlt_ml.candidate_ranker \
  --data /root/rlt/ready-v1 \
  --predictions /root/rlt/backups/embedding-results/run-20261001/qwen-4b/predictions.jsonl \
  --model /root/rlt/runs/ranker-20261001-b/ranker.cbm \
  --out /root/rlt/runs/full-chain-ranker-validation
```

### Эксперимент с карточками поставщиков

Сборка вариантов A–D выполняется на сервере данных рядом с DuckDB; перед ней
установите актуальный ML-пакет из `/root/rlt/work/ml`. Производные карточки
переносятся на GPU напрямую между серверами. Тексты и выборочные примеры остаются
на серверах.

```bash
cd /root/rlt/work/ml
/root/rlt/.venv312/bin/pip install -e '.[dev]'
PYTHONPATH=src /root/rlt/.venv312/bin/python -m rlt_ml.cards \
  --data /root/rlt/ready-v1 \
  --database /root/rlt/ready-v1/procurement.duckdb \
  --out /root/rlt/runs/card-variants \
  --config configs/supplier_cards.toml
```

На GPU с локальным кешем Qwen3-Embedding-4B выполните аудит токенов:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=src \
  /root/rlt/.venv/bin/python -m rlt_ml.card_audit \
  --variants /root/rlt/data/card-variants \
  --data /root/rlt/data/ready-v1 \
  --model Qwen/Qwen3-Embedding-4B \
  --revision 5cf2132abc99cad020ac570b19d031efec650f2b \
  --out /root/rlt/runs/card-audit
```

Оценка каждого варианта использует один набор validation-запросов, Qwen4B и
замороженные исходные карточки A для BM25; отчёт одного hybrid-прогона содержит
отдельные метрики dense и hybrid. Запуски выполняются последовательно:

```bash
cd /root/rlt/work/ml
for variant in A D; do
  length=256
  [ "$variant" = D ] && length=512
  HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=src \
    /root/rlt/.venv/bin/python -m rlt_ml.retrieval \
    --data /root/rlt/data/ready-v1 \
    --out "/root/rlt/runs/card-retrieval/$variant" \
    --split validation --model Qwen/Qwen3-Embedding-4B --hybrid \
    --config configs/compare_qwen.toml --batch-size 1 --card-max-length "$length" \
    --cards "/root/rlt/data/card-variants/$variant/cards.parquet" \
    --lexical-cards /root/rlt/data/card-variants/A/cards.parquet \
    --gpu-memory-fraction 0.68 --cpu-threads 2
done
PYTHONPATH=src /root/rlt/.venv/bin/python -m rlt_ml.compare_cards \
  --predictions-dir /root/rlt/runs/card-retrieval \
  --variants AD \
  --out /root/rlt/runs/card-retrieval/paired-comparison.json
```
## Проверка поиска поставщиков

Откройте https://rlt.goatwhistle.ru/, загрузите CSV,
откройте результат закупки. Поиск по тексту — на главной странице.

Лимиты загрузки задают переменные `UPLOAD_*`. Эндпоинты и коды ошибок описаны
в [backend/README.md](../backend.md#http-api), примеры ответов — в
[contracts](../../contracts). Проверка API: `GET /api/health/live`.

Аналитика каталога: страница `/analytics`, API `/api/analytics/*`, пересчёт
среза — сервис `analytics-worker` (`docker compose --profile workers up
analytics-worker`), настройки `ANALYTICS_*` — в
[backend/README.md](../backend.md#аналитика-каталога).

Прогресс ProductCenter сохраняется в `crawl-progress.json` внутри постоянного
тома `productcenter-cache`. Подтверждение порции записывается после успешного
INSERT; после перезапуска незавершённая порция повторяется, подтверждённые
карточки пропускаются. До завершения обхода сохраняется его исходная отметка
времени. Не удаляйте этот том при обычном обновлении сервисов.

### Архивные основания рекомендаций

При `RLT_RUN_SEARCH=true` CD импортирует основания для текущего индекса перед запуском
API. `RLT_HISTORY_DIR` (по умолчанию `/root/rlt/ready-v1`) содержит read-only
`procurement.duckdb`; граница истории берётся из manifest индекса (2024-12-01 для validation,
2025-06-01 для test).
В ClickHouse сохраняются до пяти закупок на поставщика и категорию, точное число
закупок и однозначных побед. Повторный запуск проверяет полноту и не дублирует данные.
Ссылки в карточке открывают архивную запись в пределах сессии загрузки.
Результат процедуры не трактуется как подтверждение исполнения или текущего наличия.

Ранжировщик подключается автоматически, если рядом с индексом есть
`ranker/runtime.json`, `ranker.cbm` и снимки статистики. Перед загрузкой проверяются
хеши, список признаков и соответствие карточкам; без артефакта работает гибридный
поиск. Артефакт экспортируется только после положительной оценки на закрытом test:

```bash
python -m rlt_ml.reranking.candidates --data /data/ready --vectors /data/vectors --out /data/candidates --split train --customer-dropout 0.5
python -m rlt_ml.reranking.train --train /data/train-candidates --validation /data/validation-candidates --text-validation /data/validation-text-candidates --out /data/models
python -m rlt_ml.reranking.evaluate --models /data/models --candidates /data/test-candidates --out /data/models/test-report.json
python -m rlt_ml.reranking.export --models /data/models --vectors /data/test-vectors --data /data/ready --out /data/release-index
```

Команды выполняются на сервере в окружении `ml`. В Git входят только код и
агрегированные результаты; данные, векторы и веса остаются вне репозитория.

## Качество рекомендаций

RANK-004: 4000 train-запросов, отдельный validation из 1000 запросов; только
Qwen3-Embedding-4B, гибридный поиск top-200 и CatBoost на кандидатах поиска.
Фактические товары целевого лота не используются как вход. Таблица — режим
**только по тексту**, без ИНН заказчика и цены, как в тестовом CSV сайта.

| Метрика validation | Гибридный поиск | Выбранный ранжировщик |
| --- | ---: | ---: |
| MRR исторического победителя | 0.2036 | 0.2577 |
| Победитель на первом месте | 13.72% | 17.89% |
| Известный участник в top-10 | 39.30% | 48.90% |
| Recall участников в top-10 | 31.96% | 39.80% |

Победитель отсутствующего retrieval-пула считается промахом. Участие в закупке —
неполная разметка релевантности, а не доказательство исполнения или наличия товара.
Шкала модели не выдаётся за вероятность победы. Выбор сделан на validation;
[отчёт сравнения вариантов](../../ml/reports/ranker-v2-validation.json) содержит все три модели.

### Независимый test

1000 новых запросов, 979 с однозначным победителем; история до 2025-06-01.
Модель и критерий принятия зафиксированы до расчёта метрик. Режим сайта —
только текст, без заказчика и цены.

| Метрика test | Гибридный поиск | Обученный ранжировщик |
| --- | ---: | ---: |
| MRR исторического победителя | 0.2007 | 0.2577 |
| Победитель на первом месте | 12.46% | 16.85% |
| Победитель в top-10 | 34.53% | 44.54% |
| Известный участник в top-10 | 41.80% | 53.60% |
| Recall участников в top-10 | 33.07% | 42.17% |

MRR вырос на 28.36% относительно baseline. Парный кластерный bootstrap по
процедурам (2000 повторов, seed=42): 95% интервал прироста MRR
**[+0.0431; +0.0707]**. Победитель найден в исходном пуле в 69.36% случаев;
остальные случаи включены в оценку как промахи. Это восстановление известных
участников и победителей, не экспертная оценка пригодности или гарантии поставки.

В дополнительном режиме с заказчиком и ценой MRR 0.2747 → 0.3400,
известный участник в top-10 — 48.0% → 60.4%. Эти поля пока не используются
рабочим текстовым поиском. На 20 test-запросах рабочий адаптер и offline
оценка дали одинаковые top-10 и баллы (максимальная разница 0.0).

[Основной test](../../ml/reports/ranker-v2-test.json),
[режим с метаданными](../../ml/reports/ranker-v2-test-full.json),
[проверка применения](../../ml/reports/ranker-v2-serving-test.json),
[журнал экспериментов](experiments.md).

### Обновление поиска от 2 октября

В CSV поддерживаются `customer_inn` и `start_price`: они передаются обученному
ранжировщику вместе с описанием. Размер всей загрузки — до 2 МБ. Для потоварки добавьте второй CSV после выбора извещений: `lot_id`, `product_name`, `okpd2_code`. Оба файла передаются вместе, позиции связываются по `lot_id` и сохраняются в результате.
Для полного сценария CSV на подготовленном сервере включите профиль `search`
(артефакты Qwen 4B и конфигурация энкодера обязательны); CD использует
`RLT_RUN_WORKERS=true`, `RLT_RUN_SEARCH=true`. Дополнительный поиск по свежим
векторам каталогов включается `SEARCH_VECTOR_URL=http://search-api:8080`.
Подробности и проверка артефактов — в `backend/README.md`.


Текстовое совпадение в описании и семантическая близость используются для отбора,
но сами по себе не подтверждают наличие запрошенного товара. Частичные совпадения
названий отображаются как предположения и не входят в подтверждённое покрытие.

Production перенесён на `51.250.72.225`: сайт `https://rlt.goatwhistle.ru`,
рабочие выпуски `/opt/rlt-hack/releases`, активный `/opt/rlt-hack/current`.
CD ветки `main` использует этот сервер. Энкодер — только
Qwen3-Embedding-4B/2560. Подготовка локального FP16 runtime на V100 и проверка
совместимости описаны в `deploy/README.md`; переключение требует проверки. Данные CPU сохранены в `/root/rlt`, материалы
обучения — `/opt/rlt-hack/training-gpu`. Настройки и секреты остаются на сервере.

Парные CSV отправляются вместе: извещения (`file`) и потоварка (`items_file`).
Запросы энкодеру обрабатываются батчами до 16; все позиции сохраняются.
Заданные ОКПД2 повышают компании с совпадающими историческими категориями XX.XX,
затем используется CatBoost. Совпадение категории не означает точное покрытие позиций.


Исторические основания показывают конкретные позиции с названием закупки,
датой и ссылкой. Они обозначены отдельно от текущего ассортимента и наличия.
Полный архив импортируется до среза модели с проверкой SHA256 и итоговых количеств;
после завершения примеры выбираются из всей истории, а не пяти строк карточки.
При повторном открытии сохраняется подбор оснований для исходного запроса,
включая отсутствие подходящих закупок; обновление реквизитов компании его не заменяет.
