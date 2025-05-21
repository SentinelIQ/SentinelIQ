from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Tag routes
    path('tags/', views.TagListView.as_view(), name='tag_list'),
    path('tags/create/', views.TagCreateView.as_view(), name='tag_create'),
    path('tags/<int:pk>/update/', views.TagUpdateView.as_view(), name='tag_update'),
    path('tags/<int:pk>/delete/', views.TagDeleteView.as_view(), name='tag_delete'),
    
    # Observable routes
    path('observables/', views.observable_list, name='observable_list'),
    path('observables/create/', views.observable_create, name='observable_create'),
    path('observables/<int:pk>/', views.observable_detail, name='observable_detail'),
    path('observables/<int:pk>/update/', views.observable_update, name='observable_update'),
    path('observables/<int:pk>/delete/', views.observable_delete, name='observable_delete'),
    
    # Observable association routes for alerts
    path('alerts/<int:alert_id>/observables/add/', views.add_alert_observable, name='add_alert_observable'),
    path('alerts/<int:alert_id>/observables/<int:observable_id>/remove/', views.remove_alert_observable, name='remove_alert_observable'),
    
    # Observable association routes for cases
    path('cases/<int:case_id>/observables/add/', views.add_case_observable, name='add_case_observable'),
    path('cases/<int:case_id>/observables/<int:observable_id>/remove/', views.remove_case_observable, name='remove_case_observable'),
    
    # MITRE ATT&CK routes
    path('mitre-attack/', views.mitre_attack_list, name='mitre_attack_list'),
    
    # MITRE ATT&CK API routes
    path('api/tactics/<int:tactic_id>/techniques/', views.api_get_techniques_by_tactic, name='api_get_techniques_by_tactic'),
    path('api/techniques/<int:technique_id>/subtechniques/', views.api_get_subtechniques_by_technique, name='api_get_subtechniques_by_technique'),
    
    # MITRE ATT&CK association routes for cases
    path('cases/<int:case_id>/mitre-attack/add/', views.add_case_mitre_attack, name='add_case_mitre_attack'),
    path('cases/<int:case_id>/mitre-attack/<str:item_type>/<int:item_id>/remove/', views.remove_case_mitre_attack, name='remove_case_mitre_attack'),
    
    # MITRE ATT&CK association routes for alerts
    path('alerts/<int:alert_id>/mitre-attack/add/', views.add_alert_mitre_attack, name='add_alert_mitre_attack'),
    path('alerts/<int:alert_id>/mitre-attack/<str:item_type>/<int:item_id>/remove/', views.remove_alert_mitre_attack, name='remove_alert_mitre_attack'),
] 