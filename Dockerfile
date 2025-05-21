FROM python:3.11-slim

WORKDIR /app

# Configurar variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependências
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt /app/

# Instalar dependências do Python
RUN pip install --no-cache-dir -U pip &&\
    pip install --no-cache-dir -r requirements.txt

# Copiar arquivos do projeto
COPY . /app/

# Tornar o script de entrada executável
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Expor a porta
EXPOSE 8000

# Configurar entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Comando para iniciar o servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"] 