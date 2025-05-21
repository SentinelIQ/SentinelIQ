# SentinelIQ

SentinelIQ é um sistema de gerenciamento de alertas e organizações desenvolvido em Django.

## Funcionalidades

- Gerenciamento de organizações
- Controle de usuários com diferentes níveis de acesso (Super Admin, Admin da Organização, Analista)
- Sistema de alertas com severidade e status
- Dashboards personalizados para cada tipo de usuário
- Interface responsiva e moderna

## Requisitos

- Python 3.8+
- Django 5.2+
- Outras dependências listadas em requirements.txt

## Instalação

1. Clone o repositório:
```
git clone https://github.com/seu-usuario/sentineliq.git
cd sentineliq
```

2. Crie e ative um ambiente virtual:
```
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
```

3. Instale as dependências:
```
pip install -r requirements.txt
```

4. Configure o banco de dados:
```
python manage.py migrate
```

5. Inicialize o sistema com uma organização padrão e um superadmin:
```
python manage.py initialize_system --username admin --password senha_segura --email admin@exemplo.com --org-name "Minha Organização"
```

6. Inicie o servidor de desenvolvimento:
```
python manage.py runserver
```

7. Acesse http://127.0.0.1:8000/ no seu navegador

## Estrutura do Projeto

- `accounts/`: App para gerenciamento de usuários
- `organizations/`: App para gerenciamento de organizações
- `alerts/`: App para gerenciamento de alertas
- `core/`: App com funcionalidades centrais do sistema
- `config/`: Configurações do projeto Django
- `static/`: Arquivos estáticos (CSS, JS, imagens)
- `templates/`: Templates HTML do projeto

## Níveis de Acesso

1. **Super Admin**:
   - Gerencia todas as organizações
   - Cria e gerencia todos os usuários
   - Acesso total ao sistema

2. **Admin da Organização**:
   - Gerencia usuários dentro da sua organização
   - Gerencia alertas da sua organização
   - Acesso limitado à sua organização

3. **Analista**:
   - Visualiza e atualiza alertas
   - Acesso limitado à sua organização

## Contribuindo

Contribuições são bem-vindas! Por favor, sinta-se à vontade para enviar um Pull Request.

## Configuração com Docker

### Pré-requisitos
- Docker
- Docker Compose

### Configuração para Desenvolvimento

1. Clone o repositório:
```
git clone <repositório>
cd sentineliq
```

2. Crie um arquivo .env baseado no .env.example (opcional para desenvolvimento):
```
cp .env.example .env
```

3. Inicie os serviços:
```
docker-compose up -d
```

4. Acesse o aplicativo em [http://localhost:8000](http://localhost:8000)

5. O sistema já é inicializado automaticamente com:
   - Usuário admin: admin
   - Senha: admin123
   - Email: admin@example.com
   - Organização: SentinelIQ

   Você pode personalizar esses valores editando o arquivo .env ou alterando as variáveis de ambiente no docker-compose.yml.

### Configuração para Produção

1. Clone o repositório:
```
git clone <repositório>
cd sentineliq
```

2. Crie um arquivo .env baseado no .env.example:
```
cp .env.example .env
```

3. Edite o arquivo .env com as configurações de produção, especialmente:
   - SECRET_KEY (uma chave secreta única)
   - ALLOWED_HOSTS (domínios permitidos)
   - DEBUG (definir como False)
   - ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_EMAIL (credenciais do superadmin)
   - ORG_NAME (nome da organização padrão)

4. Inicie os serviços de produção:
```
docker-compose --profile prod up -d
```

5. Acesse o aplicativo na porta 80 do seu servidor

### Comandos Úteis

- Visualizar logs:
```
docker-compose logs -f
```

- Reiniciar os serviços:
```
docker-compose restart
```

- Parar os serviços:
```
docker-compose down
```

- Aplicar migrações manualmente:
```
docker-compose exec web python manage.py migrate
```

- Coletar arquivos estáticos manualmente:
```
docker-compose exec web python manage.py collectstatic --noinput
```

- Executar o comando de inicialização do sistema manualmente:
```
docker-compose exec web python manage.py initialize_system --username admin --password senha_segura --email admin@exemplo.com --org-name "Minha Organização"
```
