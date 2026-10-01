# rlt-hack

## Задание

- [Презентация организаторов](task/docs/presentation.pdf)
- [Текстовая транскрипция презентации](task/docs/presentation.md)

## Данные

Исходные данные задачи находятся в `task/data/` и хранятся через Git LFS.
Перед клонированием установите Git LFS. После клонирования выполните `git lfs pull`, если данные не загрузились автоматически.

## Требования

- Node.js 24+
- Docker с Compose v2 — для запуска в контейнерах

## Запуск через Docker Compose

```bash
docker compose up --build
```

Фронтенд будет доступен на `http://localhost:8080`.

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `WEB_PORT` | `8080` | Порт фронтенда на хосте |
| `VITE_API_BASE_URL` | `/api` | Базовый URL API при сборке |

## Frontend

```bash
cd frontend
npm ci --silent
cp .env.example .env.local
npm run dev
```

| Команда | Что делает |
| --- | --- |
| `npm run dev` | Dev-сервер на `http://localhost:5173` |
| `npm run build` | Проверка типов и production-сборка в `dist/` |
| `npm run rules` | Правила репозитория: длина файлов, комментарии, CSS, i18n |
| `npm run lint` / `npm run format` | Biome: проверка / автоисправление |
| `npm run typecheck` | TypeScript |
| `npm test` | Unit- и компонентные тесты |
| `npm run test:coverage` | Тесты с порогом покрытия 80 % |
| `npm run e2e` | Playwright + axe; перед первым запуском выполните `npx playwright install chromium` |
| `npm run verify` | Всё, кроме e2e; должно проходить перед сдачей |

Переменные окружения фронтенда (`frontend/.env.local`):

| Переменная | Назначение |
| --- | --- |
| `VITE_API_BASE_URL` | Базовый URL API, по умолчанию `/api` |
| `VITE_API_PROXY` | Адрес backend для прокси `/api` в dev-режиме |

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

GPU-проверка запускается через `rlt-gpu-check`. Замеры качества и ресурсов, ограничения метрик и фактические результаты ведутся в [журнале экспериментов](ml/EXPERIMENTS.md).
