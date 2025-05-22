from django.urls import path
from . import views

app_name = 'cases'

urlpatterns = [
    path('', views.CaseListView.as_view(), name='case_list'),
    path('<int:pk>/', views.CaseDetailView.as_view(), name='case_detail'),
    path('create/', views.CaseCreateView.as_view(), name='case_create'),
    path('<int:pk>/update/', views.CaseUpdateView.as_view(), name='case_update'),
    path('<int:pk>/delete/', views.CaseDeleteView.as_view(), name='case_delete'),
    path('<int:pk>/comment/', views.add_case_comment, name='add_case_comment'),
    path('<int:pk>/attachment/', views.add_case_attachment, name='add_case_attachment'),
    path('<int:pk>/attachments/<int:attachment_id>/delete/', views.delete_case_attachment, name='delete_case_attachment'),
    path('<int:pk>/timeline/event/', views.add_case_event, name='add_case_event'),
    
    # Task management
    path('<int:case_id>/tasks/add/', views.add_case_task, name='add_case_task'),
    path('<int:case_id>/tasks/<int:task_id>/update/', views.update_case_task, name='update_case_task'),
    path('<int:case_id>/tasks/<int:task_id>/delete/', views.delete_case_task, name='delete_case_task'),
    path('<int:case_id>/tasks/<int:task_id>/toggle/', views.toggle_task_status, name='toggle_task_status'),

    # URLs para gerenciar categorias de ameaças e templates de tarefas
    path('threat-categories/', views.ThreatCategoryListView.as_view(), name='threat_category_list'),
    path('threat-categories/<int:pk>/', views.ThreatCategoryDetailView.as_view(), name='threat_category_detail'),
    path('threat-categories/create/', views.ThreatCategoryCreateView.as_view(), name='threat_category_create'),
    path('threat-categories/<int:pk>/update/', views.ThreatCategoryUpdateView.as_view(), name='threat_category_update'),
    
    # URLs para gerenciar templates de tarefas
    path('task-templates/', views.TaskTemplateListView.as_view(), name='task_template_list'),
    path('task-templates/create/', views.TaskTemplateCreateView.as_view(), name='task_template_create'),
    path('task-templates/<int:pk>/update/', views.TaskTemplateUpdateView.as_view(), name='task_template_update'),
    path('task-templates/<int:pk>/delete/', views.TaskTemplateDeleteView.as_view(), name='task_template_delete'),
    path('task-templates/<int:pk>/clone/', views.clone_task_template, name='task_template_clone'),
    path('task-templates/<int:pk>/toggle-status/', views.toggle_template_status, name='task_template_toggle_status'),
    path('task-templates/bulk-create/', views.bulk_create_templates, name='task_template_bulk_create'),
] 