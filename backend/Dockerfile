FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY migration ./migration
# Справочники ОКПД2, рубрик, словаря и ОКЕИ нужны нормализатору и классификатору.
COPY reference ./reference
COPY src ./src
COPY main.py ./

FROM base AS api

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin api

USER api

EXPOSE 8000

CMD ["uvicorn", "src.controller.api.main:build_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header", "--no-access-log"]

FROM base AS job

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
