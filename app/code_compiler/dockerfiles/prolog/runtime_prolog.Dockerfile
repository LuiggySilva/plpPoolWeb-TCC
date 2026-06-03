FROM debian:stable-slim
RUN apt-get update && apt-get install -y \
    swi-prolog \
    bash \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m runner
WORKDIR /code
USER runner
