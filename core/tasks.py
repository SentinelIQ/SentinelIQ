import logging
from datetime import datetime

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def sample_task():
    """Exemplo de tarefa que simplesmente registra a data e hora atuais."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    logger.info(f"Tarefa de exemplo executada às {now}")
    return f"Tarefa executada com sucesso às {now}"


@shared_task
def process_data(data):
    """Exemplo de tarefa que processa dados recebidos como parâmetro."""
    logger.info(f"Processando dados: {data}")
    # Simulando processamento
    result = f"Dados processados: {data}"
    logger.info(f"Resultado: {result}")
    return result


@shared_task
def long_running_task(duration=10):
    """Exemplo de tarefa de longa duração."""
    import time
    
    logger.info(f"Iniciando tarefa de longa duração ({duration} segundos)")
    # Simulando processamento demorado
    time.sleep(duration)
    logger.info("Tarefa de longa duração concluída")
    return f"Tarefa concluída após {duration} segundos" 