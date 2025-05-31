###########
# BUILDER #
###########
FROM python:3.13.3-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

# instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    curl gcc libpq-dev python3-dev musl-dev \
    && apt-get clean

# instalar Poetry 2.x (instalador atualizado)
ENV POETRY_HOME="/opt/poetry"
ENV PATH="${POETRY_HOME}/bin:${PATH}"
RUN curl -sSL https://install.python-poetry.org | python3 -

# desativar criação de venv separada (instalar direto no sistema)
RUN poetry config virtualenvs.create false

# copiar e instalar dependências
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

# copiar o restante do projeto
COPY . .

#########
# FINAL #
#########
FROM python:3.13.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# instalar libs do sistema
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev libglib2.0-0 && apt-get clean

# criar diretórios da aplicação
ENV HOME=/home/app
ENV APP_HOME=/home/app/web
RUN mkdir -p $APP_HOME/staticfiles $APP_HOME/mediafiles
WORKDIR $APP_HOME

# copiar arquivos do builder
COPY --from=builder /usr/src/app /home/app/web
COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/src/app /home/app/web

# copiar e configurar o entrypoint
COPY ./entrypoint.sh .
RUN sed -i 's/\r$//g' $APP_HOME/entrypoint.sh && chmod +x $APP_HOME/entrypoint.sh

# criar usuário e definir permissões
RUN groupadd -r app && useradd -r -g app app && chown -R app:app $APP_HOME
USER app

EXPOSE 8000

ENTRYPOINT ["/home/app/web/entrypoint.sh"]