from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Dashboard URL
    path('dashboard/', views.NotificationDashboardView.as_view(), name='dashboard'),
    
    # Notification Destination URLs
    path('destinations/', views.NotificationDestinationListView.as_view(), name='destination_list'),
    path('destinations/create/', views.NotificationDestinationCreateView.as_view(), name='destination_create'),
    path('destinations/<int:pk>/', views.NotificationDestinationDetailView.as_view(), name='destination_detail'),
    path('destinations/<int:pk>/edit/', views.NotificationDestinationUpdateView.as_view(), name='destination_update'),
    path('destinations/<int:pk>/delete/', views.NotificationDestinationDeleteView.as_view(), name='destination_delete'),
    path('destinations/<int:pk>/test/', views.test_notification_destination, name='destination_test'),
    
    # Notification Rule URLs
    path('rules/', views.NotificationRuleListView.as_view(), name='rule_list'),
    path('rules/create/', views.NotificationRuleCreateView.as_view(), name='rule_create'),
    path('rules/<int:pk>/', views.NotificationRuleDetailView.as_view(), name='rule_detail'),
    path('rules/<int:pk>/edit/', views.NotificationRuleUpdateView.as_view(), name='rule_update'),
    path('rules/<int:pk>/delete/', views.NotificationRuleDeleteView.as_view(), name='rule_delete'),
    
    # Notification Log URLs
    path('logs/', views.NotificationLogListView.as_view(), name='log_list'),
    path('logs/<int:pk>/', views.NotificationLogDetailView.as_view(), name='log_detail'),
    path('logs/<int:pk>/retry/', views.retry_notification, name='log_retry'),
    
    # Webhook API for external systems to trigger notifications
    path('api/webhook/<str:token>/', views.webhook_receiver, name='webhook_receiver'),
] 