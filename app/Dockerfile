###########
# BUILDER #
###########
FROM python:3.13.3-slim AS builder

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y curl && apt-get clean

ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:${PATH}"
RUN curl -sSL https://install.python-poetry.org | python3 -

RUN poetry self add poetry-plugin-export

COPY pyproject.toml poetry.lock ./

RUN poetry export --only main --without-hashes -f requirements.txt -o requirements.txt

#########
# FINAL #
#########
FROM python:3.13.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev libglib2.0-0 gcc python3-dev \
    gosu netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir -p $APP_HOME/staticfiles $APP_HOME/mediafiles
WORKDIR $APP_HOME

COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

RUN sed -i 's/\r$//g' $APP_HOME/entrypoint.sh && chmod +x $APP_HOME/entrypoint.sh

RUN groupadd -r app && useradd -r -g app app && chown -R app:app $APP_HOME

EXPOSE 8000

ENTRYPOINT ["/home/app/web/entrypoint.sh"]