# Образ джобы сбора: команды миграций и обхода источников.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libxml2 и libxslt нужны lxml, которым адаптеры разбирают HTML каталогов и карточек.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Зависимости объявлены один раз — в pyproject.toml.
COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY migration ./migration
COPY src ./src
COPY main.py ./

ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
