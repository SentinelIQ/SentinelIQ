from django.urls import path

from .views import HomePageView, process_data_view, trigger_task

app_name = "core"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("tasks/trigger/", trigger_task, name="trigger_task"),
    path("tasks/process-data/", process_data_view, name="process_data"),
]
