# sudo docker build -t plp-pool-web .             Criar imagem
# sudo docker run -d -t --name plpPoolCompiler plp-pool-compiler                Criar container com essa imagem
# sudo docker exec -it <container_id> bash              Executar o bash do container
# sudo docker image ls              Ver imagens
# sudo docker ps                    Ver containers
# sudo docker rmi -f <image_id>     Remover imagem
# sudo docker rm -f <container_id>  Remover container
# sudo docker-compose up -d --build
# docker-compose exec web python manage.py migrate
# docker-compose exec web python manage.py createsuperuser

FROM alpine:latest

LABEL maintainer="luiggy.silva@ccc.ufcg.edu.br"
LABEL version="1.0"
LABEL description="This is custom Docker Image for run python, c/c++, haskell and prolog scripts."

# Atualiza a lista de pacotes e instala as dependências
# Update the package index and install required dependencies
RUN apk update && apk add build-base python3-dev wget gmp-dev make postgresql-client

# Install Haskell
RUN apk add ghc

# Install Prolog
#RUN apk add swi-prolog
RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories && apk update && apk add --no-cache swi-prolog

# Install C++ and C compilers
RUN apk add g++ gcc

# Instala o pip
RUN python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --no-cache-dir --upgrade pip setuptools

ENV PYTHONUNBUFFERED 1

# Define o diretório de trabalho
WORKDIR /project

# Copia o conteúdo do diretório atual para o diretório de trabalho no container
COPY . /project

# Instala as dependências do Python a partir do arquivo requirements.txt
#RUN pip3 install --no-cache-dir -r requirements.txt

COPY Pipfile Pipfile.lock /project/
RUN pip3 install pipenv && pipenv install --system
