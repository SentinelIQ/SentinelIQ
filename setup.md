# SentinelIQ Sistema - Guia de Inicialização

Este documento explica como iniciar o sistema SentinelIQ, realizar migrações e importar dados usando comandos do Django.

## 1. Configuração Inicial

### 1.1 Preparar o ambiente

Certifique-se de que o Docker e o Docker Compose estejam instalados no seu sistema.

### 1.2 Configurar variáveis de ambiente

**Windows (PowerShell):**
```powershell
Copy-Item -Path .env.example -Destination .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

Edite o arquivo `.env` conforme necessário para configurar as variáveis de ambiente.

## 2. Iniciar o sistema com Docker

**Windows/Linux/Mac:**
```bash
docker-compose up -d
```

Este comando iniciará todos os serviços definidos no `docker-compose.yml`, incluindo o banco de dados, Redis e a aplicação Django.

## 3. Executar migrações

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py migrate
```

Este comando criará todas as tabelas necessárias no banco de dados.

## 4. Inicializar o sistema

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py initialize_system
```

Este comando configura os dados básicos do sistema, incluindo:
- Organização padrão
- Usuário superadmin
- Categorias de ameaças

## 5. Importar dados MITRE ATT&CK

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py import_mitre_data
```

Este comando importa a base de dados MITRE ATT&CK para o sistema, incluindo táticas, técnicas e subtécnicas.

## 6. Verificar a importação MITRE

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py verify_mitre_import
```

## 7. Criar templates de tarefas

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py create_task_templates
```

Cria templates de tarefas padrão para cada categoria de ameaça.

## 8. Configurar tarefas periódicas para todos os módulos

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py setup_core_periodic_tasks
docker-compose exec web python manage.py setup_accounts_periodic_tasks
docker-compose exec web python manage.py setup_alerts_periodic_tasks
docker-compose exec web python manage.py setup_cases_periodic_tasks
docker-compose exec web python manage.py setup_organizations_periodic_tasks
docker-compose exec web python manage.py setup_vision_periodic_tasks
```

Estes comandos configuram tarefas periódicas do Celery para cada módulo do sistema.

## 9. Verificar a integridade dos templates

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py validate_templates
```

Este comando verifica se todas as views têm templates correspondentes.

## 10. Acessar o sistema

Após concluir a inicialização, você pode acessar o sistema no navegador:

- URL: http://localhost:8000
- Usuário: admin
- Senha: (definida durante a execução do comando initialize_system)

## 11. Comandos adicionais úteis

### Sincronizar com instâncias MISP

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py sync_misp
```

### Criar um superusuário adicional

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py createsuperuser
```

### Coletar arquivos estáticos

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Testar o sistema de notificações

**Windows/Linux/Mac:**
```bash
docker-compose exec web python manage.py test_notification
```

## 12. Encerrar o sistema

**Windows/Linux/Mac:**
```bash
docker-compose down
```

Para encerrar o sistema e remover volumes:

**Windows/Linux/Mac:**
```bash
docker-compose down -v
```

## Observações

- Todos os dados são armazenados em um banco de dados PostgreSQL definido no docker-compose.yml
- O sistema utiliza Celery com Redis para tarefas assíncronas e agendadas
- Os templates devem ser mantidos no padrão `/templates/nome_modulo` para garantir a compatibilidade 