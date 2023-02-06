# TCC - plpPoolWeb

Essa aplicação web tem por objetivo dar suporte ao professor e monitores da disciplina Paradigma de Linguagens de Programação do curso de Ciência da Computação da UFCG. A disciplina trabalha com laboratórios práticos de programação em diferentes paradigmas. A aplicação irá permitir que os monitores da disciplina possam submeter questões para compor os laboratórios de programação. Para tal, eles precisam registrar detalhes sobre essas questões (e.g., texto, casos de teste, assuntos abordados) e poder ver e comparar com as questões de períodos anteriores. Além disso, a aplicação deve ter uma visão para o professor da disciplina. Nessa visão o professor deve poder filtrar questões por categorias, objetivos, etc, bem como avaliar e sugerir modificações para os monitores.

# Execução local:


1. Docker e docker-compose instalados na máquina: [Docker](https://www.docker.com/products/docker-desktop/)
2. Clonar o repositório
3. Criar um arquivo `.env` dentro do diretório do projeto com as seguintes variáveis:
```
DEBUG=<bool>
SECRET_KEY=<string>
EMAIL_HOST=<string>
EMAIL_PORT=<int>
EMAIL_HOST_USER=<string>
EMAIL_HOST_PASSWORD=<string>
SERVER_EMAIL=<string>
```
4. Dentro do diretório criar a imagem do Dockerfile com o comando: `docker build -t plp-pool-web .`
5. Após a criação da imagem, executar a aplicação com o comando (digite **y** caso apareça *Continue with the new image? [yN]* ): `docker-compose up -d --build`
6. Realizar a migração da base de dados com o seguinte comando: `docker-compose exec web python manage.py migrate`
7. Criar um supe-usuário com email e senha válidos (acesso a pagina de admin): `docker-compose exec web python manage.py createsuperuser`

A aplicação estará disponivel na url: http://127.0.0.1:8000/

Para **interroper a execução da aplicação** basta executar o seguinte comando: `docker-compose down`
