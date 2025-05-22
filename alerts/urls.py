from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.AlertListView.as_view(), name='alert_list'),
    path('<int:pk>/', views.AlertDetailView.as_view(), name='alert_detail'),
    path('create/', views.AlertCreateView.as_view(), name='alert_create'),
    path('<int:pk>/update/', views.AlertUpdateView.as_view(), name='alert_update'),
    path('<int:pk>/delete/', views.AlertDeleteView.as_view(), name='alert_delete'),
    path('<int:pk>/escalate/', views.escalate_to_case, name='escalate_to_case'),
    path('<int:alert_id>/comments/add/', views.add_alert_comment, name='add_alert_comment'),
    path('<int:alert_id>/related/', views.related_alerts, name='related_alerts'),
    path('<int:alert_id>/related/add/', views.add_related_alert, name='add_related_alert'),
    path('<int:alert_id>/related/<int:related_id>/remove/', views.remove_related_alert, name='remove_related_alert'),
    
    # Custom fields management
    path('custom-fields/', views.AlertCustomFieldListView.as_view(), name='alert_custom_field_list'),
    path('custom-fields/create/', views.AlertCustomFieldCreateView.as_view(), name='alert_custom_field_create'),
    path('custom-fields/<int:pk>/update/', views.AlertCustomFieldUpdateView.as_view(), name='alert_custom_field_update'),
    path('custom-fields/<int:pk>/delete/', views.AlertCustomFieldDeleteView.as_view(), name='alert_custom_field_delete'),
] 