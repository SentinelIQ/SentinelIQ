from django.urls import path
from . import views

urlpatterns = [
    # Tags
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:pk>/update/', views.tag_update, name='tag_update'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='tag_delete'),
    
    # Observables
    path('observables/', views.observable_list, name='observable_list'),
    path('observables/create/', views.observable_create, name='observable_create'),
    path('observables/<int:pk>/', views.observable_detail, name='observable_detail'),
    path('observables/<int:pk>/update/', views.observable_update, name='observable_update'),
    path('observables/<int:pk>/delete/', views.observable_delete, name='observable_delete'),
    
    # Alert Observables
    path('alerts/<int:alert_id>/observables/add/', views.add_alert_observable, name='add_alert_observable'),
    path('alerts/<int:alert_id>/observables/<int:observable_id>/remove/', views.remove_alert_observable, name='remove_alert_observable'),
    
    # Case Observables
    path('cases/<int:case_id>/observables/add/', views.add_case_observable, name='add_case_observable'),
    path('cases/<int:case_id>/observables/<int:observable_id>/remove/', views.remove_case_observable, name='remove_case_observable'),
] 