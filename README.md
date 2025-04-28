# SentinelIQ

SentinelIQ é um projeto Django usando práticas modernas de desenvolvimento.

## Requisitos

- Python 3.13+
- Poetry para gerenciamento de dependências
- Docker e Docker Compose (opcional, para ambiente containerizado)

## Tecnologias

- Django 5.2
- PostgreSQL
- Redis
- Poetry
- Docker
- Nginx

## Configuração do Ambiente de Desenvolvimento

### Usando Poetry (Desenvolvimento Local)

1. Clone o repositório:
   ```bash
   git clone <repositório>
   cd sentineliq
   ```

2. Instale as dependências usando Poetry:
   ```bash
   poetry install
   ```

3. Configure o arquivo .env para desenvolvimento local:
   ```bash
   cp .env.local .env
   ```

4. Aplique as migrações:
   ```bash
   poetry run python manage.py migrate
   ```

5. Execute o servidor de desenvolvimento:
   ```bash
   poetry run python manage.py runserver
   ```

### Usando Docker

1. Clone o repositório:
   ```bash
   git clone <repositório>
   cd sentineliq
   ```

2. Configure o arquivo .env:
   ```bash
   cp .env.template .env
   ```
   
   O arquivo .env já está configurado para usar os serviços do Docker:
   ```
   DATABASE_URL=postgres://postgres:postgres@db:5432/sentineliq
   REDIS_URL=redis://redis:6379/0
   ```

3. Construa e inicie os containers:
   ```bash
   docker-compose up -d --build
   ```

4. Aplique as migrações:
   ```bash
   docker-compose exec web poetry run python manage.py migrate
   ```

5. Crie um superusuário para acessar o admin (opcional):
   ```bash
   docker-compose exec web poetry run python manage.py createsuperuser
   ```

## Estrutura do Projeto

O projeto segue a estrutura padrão do Django, organizada da seguinte maneira:

```
sentineliq/
  ├── sentineliq/            # Configuração principal do projeto
  │   ├── settings.py        # Configurações do Django
  │   ├── urls.py            # Definições de URLs
  │   ├── wsgi.py            # Configuração WSGI para produção
  │   └── asgi.py            # Configuração ASGI para produção
  ├── manage.py              # Script de gerenciamento do Django
  ├── pyproject.toml         # Configuração do Poetry
  ├── Dockerfile             # Configuração do Docker
  ├── docker-compose.yml     # Configuração do Docker Compose
  └── nginx/                 # Configuração do Nginx
      └── nginx.conf         # Arquivo de configuração do Nginx
```

## Desenvolvimento

Para adicionar um novo aplicativo Django ao projeto:

```bash
poetry run python manage.py startapp nome_do_app
```

Após criar um app, adicione-o à lista INSTALLED_APPS em settings.py.

## Testes

Execute os testes usando pytest:

```bash
poetry run pytest
```

## Implantação em Produção

Para ambientes de produção, siga estas recomendações:

1. Configure variáveis de ambiente seguras (não use os valores padrão)
2. Configure DEBUG=False
3. Configure um SECRET_KEY seguro
4. Configure ALLOWED_HOSTS apropriadamente
5. Use HTTPS para todas as conexões
6. Configure corretamente o PostgreSQL para produção

## Licença

Este projeto está licenciado sob [inserir licença].

## Development Workflow

### Git Flow

This project follows Git Flow for branch management:

- `main`: Production code
- `develop`: Development branch for integration
- `feature/*`: New features
- `release/*`: Release preparation
- `hotfix/*`: Production hotfixes

### Conventional Commits

We use Conventional Commits for consistent commit messages:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only changes
- `style`: Changes that don't affect the code's meaning
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `test`: Adding missing tests or correcting existing tests
- `chore`: Changes to the build process or auxiliary tools

### CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment:

1. On any push or pull request to `develop` or `main`:
   - Code is tested with pytest
   - Linting checks are performed
   - Test coverage is reported

2. On push to `develop`:
   - Docker image is built and tagged as `develop`
   - Image is pushed to DockerHub

3. On push to `main`:
   - Docker image is built and tagged with version/branch
   - Image is pushed to DockerHub
   - Deployment to production environment is triggered automatically

### Setup CI/CD

To configure CI/CD for your repository:

1. Add the following secrets to your GitHub repository:
   - `DOCKERHUB_USERNAME`: Your DockerHub username
   - `DOCKERHUB_TOKEN`: Your DockerHub access token
   - `PRODUCTION_HOST`: Production server hostname/IP
   - `PRODUCTION_USERNAME`: SSH username for production server
   - `PRODUCTION_SSH_KEY`: SSH private key for production server

2. Ensure Docker and Docker Compose are installed on your production server.

3. Update the repository URL in `yourusername/sentineliq` to your actual DockerHub repository.

### Manual Deployment

For manual deployment, use the provided script:

```bash
# For first-time setup
cp .env.template .env
# Edit .env with your environment-specific values

# Run the deployment script
./scripts/deploy.sh
```

### Release Process

1. Create a release branch from `develop`: `git flow release start vX.Y.Z`
2. Make final adjustments
3. Generate changelog: `poetry run cz bump --changelog`
4. Finish release: `git flow release finish vX.Y.Z`

For detailed instructions, use `poetry run cz --help` or `poetry run cz bump --help`. 