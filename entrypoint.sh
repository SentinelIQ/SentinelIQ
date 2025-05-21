#!/bin/sh

# Esperar pelo banco de dados estar disponível
echo "Aguardando conexão com o banco de dados..."
sleep 5

# Executar migrações
echo "Aplicando migrações..."
python manage.py migrate --noinput

# Inicializar sistema com organização e superadmin padrão
echo "Inicializando o sistema..."
python manage.py initialize_system \
  --username "${ADMIN_USERNAME:-admin}" \
  --password "${ADMIN_PASSWORD:-admin123}" \
  --email "${ADMIN_EMAIL:-admin@example.com}" \
  --org-name "${ORG_NAME:-SentinelIQ}"

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar servidor
echo "Iniciando servidor..."
exec "$@" 