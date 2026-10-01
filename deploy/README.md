# Развёртывание через GitHub Actions

Workflow `.github/workflows/ci-cd.yml` запускается для pull request, push в `main`
и вручную. На PR выполняются проверки и проверка контейнеров. При включённом
`DEPLOY_ENABLED` после успешных проверок `main` образы передаются на сервер
по SSH и запускаются.
Если появился более новый коммит `main`, устаревший выпуск пропускается.

## Проверки

- Frontend: Node.js 24, `npm ci`, `npm run verify`, production-сборка,
  Playwright для desktop/mobile и axe.
- Backend: Python 3.13, Ruff, четыре проверки хранилища и джобы на искусственных
  данных, без обращения к внешним каталогам.
- ML: Python 3.12, Ruff и pytest на искусственных данных. GPU-зависимости
  не устанавливаются; GPU-тест пропускается. Датасет LFS не загружается.
- Контейнеры: ShellCheck, сборка frontend/backend, запуск отдельной тестовой БД,
  резервная копия и восстановление тестовой таблицы, миграции и их повторное
  применение, проверка HTTP и отката после заведомо неисправного выпуска.

## Сервер

Нужны Linux, Docker, Compose 2.24.4+, Bash, `flock`, OpenSSH и минимум 2 GiB
свободного диска перед загрузкой образов. Рабочая конфигурация — корневой Compose
с наложенным `deploy/compose.production.yml`.

- Пользователь: `rlt-deploy`, член группы Docker.
- Приложение и выпуски: `/opt/rlt-hack/releases/<commit>`.
- Текущий и предыдущий выпуски: `/opt/rlt-hack/current`, `/opt/rlt-hack/previous`.
- Настройки: `/etc/rlt-hack/production.env`, права `root:rlt-deploy`, `0640`.
- Внешние данные для ручного запуска джобы: `/opt/rlt-hack/data`, только чтение.
- Compose-проект: `rlt-hack`; тома БД и резервных копий сохраняются между выпусками.
- Сайт: порт 8081. ClickHouse: только localhost, 18123/19000.
- Веб-интерфейс БД запускается вручную профилем `admin`, только localhost:13488.

Фронтенд сейчас работает в демонстрационном режиме: HTTP API ещё не реализован.
Обучение ML и автоматический обход внешних источников в деплой не входят.
Сервисы других Compose-проектов и ML-каталог `/root/rlt` не обслуживаются этими
скриптами. HTTPS подключается отдельно после назначения домена.

## Первичная настройка

Создать отдельный SSH-ключ и передать на сервер его публичную часть,
`bootstrap.sh` и `production.env.example`. Запустить от root:

```sh
bash bootstrap.sh /path/to/deploy_ed25519.pub
```

Скрипт создаёт пользователя и каталоги, добавляет ключ с ограничением `restrict`
и генерирует пароль ClickHouse. При повторном запуске существующий env сохраняется.
Закрытый ключ и пароль в репозиторий не помещаются.

В GitHub создать environment `production`. Variables задать на уровне
репозитория, Secrets — в environment `production`:

| Вид | Имя | Значение |
| --- | --- | --- |
| Variable | `DEPLOY_HOST` | IP или DNS сервера |
| Variable | `DEPLOY_USER` | `rlt-deploy` |
| Variable | `DEPLOY_ENABLED` | `true` после подготовки сервера и секретов |
| Secret | `DEPLOY_SSH_KEY` | Закрытый ключ отдельного пользователя |
| Secret | `DEPLOY_KNOWN_HOSTS` | Проверенная запись публичного ключа SSH сервера |

Доступ к production environment ограничить веткой `main`. SSH-пароль root
workflow не использует. Образы передаются как артефакт Actions с SHA-256,
доступ сервера к приватному GitHub-репозиторию или registry не требуется.
До включения `DEPLOY_ENABLED` выполняется только CI, сервер не обновляется.

## Обновление и откат

`release.sh` проверяет хеши и метки ревизии образов, блокирует параллельный деплой,
поднимает ClickHouse и делает синхронный `BACKUP DATABASE` в отдельный том.
Только после успешной копии применяются миграции, затем обновляется frontend.
Ссылка `current` переключается после успешных healthcheck и HTTP-запроса.
Перезапуск frontend и ClickHouse может дать короткий перерыв в доступности.

При сбое обновления frontend скрипт возвращает его предыдущий образ. Ручной откат:

```sh
bash /opt/rlt-hack/current/deploy/rollback.sh
```

Откат приложения не откатывает миграции БД. Перед изменением схемы нужно сохранять
совместимость с предыдущим приложением; восстановление БД из копии выполняется
отдельно после проверки. Имя копии записано в `backup-before.txt` каждого выпуска.
Копии на том же сервере не заменяют внешнее резервное хранение.

Для ручных команд выбрать ревизию и конфигурацию:

```sh
cd /opt/rlt-hack/current
export RLT_IMAGE_TAG="$(basename "$(readlink -f /opt/rlt-hack/current)")"
docker compose --project-name rlt-hack --env-file /etc/rlt-hack/production.env \
  -f docker-compose.yml -f deploy/compose.production.yml ps
```

В этой команде `ps` можно заменить на `logs --tail 100 frontend clickhouse`,
`run --rm sync-job providers` или `--profile admin up -d clickhouse-ui`.
Включение источников и доступ к исходным CSV задаются серверным env.

Скрипты production не удаляют тома, резервные копии и старые выпуски.
Следить за свободным диском и вручную удалять только заведомо ненужные артефакты.
`deploy/smoke.sh` удаляет только собственное временное окружение `rlt-ci-*`.

Источники: [GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets),
[Compose healthcheck/wait](https://docs.docker.com/reference/cli/docker/compose/up/),
[резервное копирование ClickHouse](https://clickhouse.com/docs/operations/backup).
