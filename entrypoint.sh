#!/bin/bash

set -e

# Aguardar a inicialização do PostgreSQL e RabbitMQ
echo "Aguardando a inicialização dos serviços..."
sleep 10

# Aplicar migrações sempre antes de iniciar qualquer serviço
echo "Aplicando migrações do Django automaticamente..."
python manage.py migrate --no-input

# Verificar se é necessário aplicar migrações
if [[ "$1" == "migrate" ]]; then
  echo "Migrações já aplicadas, saindo..."
  exit 0
fi

# Verificar se é um comando do Celery worker
if [[ "$1" == "celery" && "$2" == "-A" && "$3" == "sentineliq" && "$4" == "worker" ]]; then
  echo "Iniciando o Celery worker..."
  exec celery -A sentineliq worker --loglevel=info
fi

# Verificar se é um comando do Celery beat
if [[ "$1" == "celery" && "$2" == "-A" && "$3" == "sentineliq" && "$4" == "beat" ]]; then
  echo "Iniciando o Celery beat..."
  exec celery -A sentineliq beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info
fi

# Caso contrário, executar o comando passado para o container
echo "Executando comando: $@"
exec "$@"
