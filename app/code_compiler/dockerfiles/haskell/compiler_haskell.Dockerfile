FROM alpine:latest
RUN apk add --no-cache ghc musl-dev bash
WORKDIR /code
RUN adduser -D runner
USER runner
