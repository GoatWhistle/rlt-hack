# Парсер и локальный эмбеддер

Три сервиса: `parser-worker` выполняет `sync --forever`, `embedder` обслуживает
локальный Qwen3-Embedding-4B Q4_K_M, `embedding-worker` опрашивает ClickHouse
каждые 30 секунд и векторизует новые/изменённые предложения. Веса предварительно
загружаются в том `embedding-models`, во время обработки внешние LLM API
не вызываются. Встроенный в другой проект Ollama не используется.

Для локального запуска подготовить `.env`, включить нужный источник и выполнить:

```sh
docker compose --profile ml up -d clickhouse embedder
docker compose run --rm migrate
docker compose exec embedder ollama pull qwen3-embedding:4b
docker compose --profile ml --profile workers up -d parser-worker embedding-worker
docker compose run --rm --no-deps embedding-worker search 'бумага для принтера'
```

Для ProductCenter задать `PRODUCTCENTER_WEB_PROVIDER=true`,
`PRODUCTCENTER_MAX_CARDS=0`, `SYNC_PARALLEL_REQUESTS=2`, `REQUEST_TIMEOUT=45`.
Остальные источники оставить выключенными до настройки и проверки их доступа.
ProductCenter сохраняет порции до 32 товаров во время обхода. При ошибке уже
записанные порции остаются доступны, в журнале стоит partial. Только успешное
завершение полного обхода разрешает снимать отсутствующие товары с продажи.
Большой обход может занять часы.
Кеш успешных страниц сохраняется между перезапусками.

Эмбеддер: localhost:11435, 2 CPU, 3500 MiB; парсер: 1 CPU, 768 MiB;
воркер векторизации: 256 MiB. Для машины с 8 ГБ RAM задайте `CLICKHOUSE_MEMORY_LIMIT=1500m`. Векторы имеют 2560 измерений, контекст 512,
батч воркера `EMBEDDING_BATCH_SIZE=16` (1–32). Неполный батч накапливается
до `EMBEDDING_BATCH_WAIT_SECONDS=5` секунд, полный отправляется сразу.
Для ограниченной памяти энкодера размер можно уменьшить до 1. Запись векторов
идёт одним INSERT на батч; ошибки оставляют предложения в очереди. CLI ищет по предложениям парсера. HTTP API сайта отдельно ищет по
историческим профилям поставщиков из готового индекса.

`EMBEDDING_MODEL_DIGEST` позволяет закрепить SHA-256 весов из `ollama list`
или `/api/tags`. В `model_key` всегда записываются фактический digest, версия
подготовки текста, контекст и размерность. Смена весов в работающем процессе
останавливает успешную обработку до перезапуска; старые векторы не смешиваются
с новой моделью. Изменённые и снятые предложения отфильтровываются при поиске.
Категория и ОКПД2 пока не добавляются в текст: действующий `content_hash` их
не покрывает. Автоматическая нормализация в `catalog_items` не выполняется.

Диагностика:

```sh
docker compose logs --tail 100 parser-worker embedding-worker embedder
docker compose run --rm --no-deps embedding-worker index --max-batches 10
python backend/tests/embedding/smoke.py
```

`backend/tests/embedding/live_smoke.py` запускается только явно на сервере.
Он читает до шести живых товаров ProductCenter, создаёт отдельную
`embedding_diagnostic_<timestamp>` БД, проверяет индексацию, повтор и три
поисковых запроса. Отчёт пишет в `/reports/embedding-live.json`; это проверка
интеграции, не оценка релевантности и не полный сбор источника. БД не удаляется
автоматически. Для запуска внутри backend-образа отдельно примонтировать
`backend/tests` в `/checks` и каталог отчётов в `/reports`, задать `PYTHONPATH=/app`.

Документация: [Ollama embed](https://docs.ollama.com/api/embed),
[официальный Qwen3-Embedding-4B Q4_K_M](https://ollama.com/library/qwen3-embedding:4b).


Прогресс ProductCenter сохраняется в `crawl-progress.json` внутри постоянного
тома `productcenter-cache`. Подтверждение порции записывается после успешного
INSERT; после перезапуска незавершённая порция повторяется, подтверждённые
карточки пропускаются. До завершения обхода сохраняется его исходная отметка
времени. Не удаляйте этот том при обычном обновлении сервисов.
