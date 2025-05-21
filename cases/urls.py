from django.urls import path
from . import views

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
] 