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

На сервере использовать `docker compose --project-name rlt-hack
--env-file /etc/rlt-hack/production.env -f docker-compose.yml
-f deploy/compose.production.yml`, находясь в каталоге исходников активного
выпуска и задав `RLT_IMAGE_TAG` его ревизией. Первичная ручная подготовка env:
`bash deploy/prepare-runtime.sh` от root. Скрипт не создаёт SSH-пользователей
или ключи; существующий env сохраняется. Настройка постоянного доступа CI/CD
выполняется отдельно.

Для ProductCenter задать `PRODUCTCENTER_WEB_PROVIDER=true`,
`PRODUCTCENTER_MAX_CARDS=0`, `SYNC_PARALLEL_REQUESTS=2`, `REQUEST_TIMEOUT=45`.
Остальные источники оставить выключенными до настройки и проверки их доступа.
Парсер сохраняет пакет только после полного обхода; при ошибке фиксируется
неуспех, частичный снимок не подменяет каталог. Большой обход может занять часы.
Кеш успешных страниц сохраняется между перезапусками.

Эмбеддер: localhost:11435, 2 CPU, 3500 MiB; парсер: 1 CPU, 768 MiB;
воркер векторизации: 256 MiB. Для сервера с 8 ГБ RAM в production env задан
`CLICKHOUSE_MEMORY_LIMIT=1500m`. Векторы имеют 2560 измерений, контекст 512,
батч 1. Поиск пока доступен через CLI; подключения к frontend HTTP API нет.

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
