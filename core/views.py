from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from .tasks import process_data, sample_task


class HomePageView(TemplateView):
    """Home page view for the application."""

    template_name = "index.html"


def trigger_task(request):
    """View para disparar uma tarefa do Celery e retornar o ID da tarefa."""
    task = sample_task.delay()
    return JsonResponse({
        "message": "Tarefa iniciada com sucesso",
        "task_id": task.id
    })


def process_data_view(request):
    """View para processar dados através do Celery."""
    data = request.GET.get("data", "Dados padrão")
    task = process_data.delay(data)
    return JsonResponse({
        "message": f"Processamento de '{data}' iniciado",
        "task_id": task.id
    })
