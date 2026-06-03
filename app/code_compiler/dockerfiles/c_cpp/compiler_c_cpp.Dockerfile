FROM alpine:latest
RUN apk add --no-cache gcc g++ musl-dev bash
WORKDIR /code
# Usuário não-root para execução
RUN adduser -D runner
USER runner
