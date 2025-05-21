# Script de inicialização do SentinelIQ
# Autor: Cursor
# Data: 2025-05-21

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "   Inicializando SentinelIQ   " -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Verifica se o Docker está em execução
try {
    $dockerStatus = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Docker não está em execução. Por favor, inicie o Docker Desktop primeiro." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERRO] Docker não está instalado ou ocorreu um erro ao verificar o status." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Docker está em execução." -ForegroundColor Green

# Diretório do projeto
$projectDir = $PSScriptRoot
Write-Host "[INFO] Diretório do projeto: $projectDir" -ForegroundColor Yellow

# Inicia os contêineres Docker
Write-Host "[INFO] Iniciando contêineres Docker..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao iniciar os contêineres Docker." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Contêineres Docker iniciados com sucesso." -ForegroundColor Green

# Aguarda o banco de dados estar pronto
Write-Host "[INFO] Aguardando o banco de dados estar pronto..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Executa as migrações
Write-Host "[INFO] Aplicando migrações do banco de dados..." -ForegroundColor Yellow
docker-compose exec web python manage.py migrate

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao aplicar migrações." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Migrações aplicadas com sucesso." -ForegroundColor Green

# Inicializa o sistema
Write-Host "[INFO] Inicializando sistema..." -ForegroundColor Yellow
docker-compose exec web python manage.py initialize_system

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao inicializar o sistema." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Sistema inicializado com sucesso." -ForegroundColor Green

# Cria templates de tarefas
Write-Host "[INFO] Criando templates de tarefas..." -ForegroundColor Yellow
docker-compose exec web python manage.py create_task_templates --force

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERRO] Falha ao criar templates de tarefas." -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Templates de tarefas criados com sucesso." -ForegroundColor Green

# Verifica os templates criados
Write-Host "[INFO] Verificando templates criados..." -ForegroundColor Yellow
docker-compose exec web python manage.py shell -c "from cases.models import TaskTemplate; print(f'Total de templates: {TaskTemplate.objects.count()}')"

# Informações de acesso
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "   SentinelIQ Inicializado!   " -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "URL: http://localhost:8000" -ForegroundColor Green
Write-Host "Usuário: admin" -ForegroundColor Green
Write-Host "Senha: admin123" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Cyan 