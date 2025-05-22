from django.urls import path
from . import views

app_name = 'core'

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
    path('mitre/', views.mitre_attack_list, name='mitre_attack_list'),
    
    # MITRE ATT&CK API routes
    path('api/mitre/tactic/<int:tactic_id>/techniques/', views.api_get_techniques_by_tactic, name='api_get_techniques_by_tactic'),
    path('api/mitre/technique/<int:technique_id>/subtechniques/', views.api_get_subtechniques_by_technique, name='api_get_subtechniques_by_technique'),
    path('api/mitre/tactic/<int:tactic_id>/', views.api_get_tactic_details, name='api_get_tactic_details'),
    path('api/mitre/technique/<int:technique_id>/', views.api_get_technique_details, name='api_get_technique_details'),
    path('api/mitre/subtechnique/<int:subtechnique_id>/', views.api_get_subtechnique_details, name='api_get_subtechnique_details'),
    
    # MITRE ATT&CK association routes for cases
    path('case/<int:case_id>/mitre/add/', views.add_case_mitre_attack, name='add_case_mitre_attack'),
    path('case/<int:case_id>/mitre/remove/<str:item_type>/<int:item_id>/', views.remove_case_mitre_attack, name='remove_case_mitre_attack'),
    
    # MITRE ATT&CK association routes for alerts
    path('alert/<int:alert_id>/mitre/add/', views.add_alert_mitre_attack, name='add_alert_mitre_attack'),
    path('alert/<int:alert_id>/mitre/remove/<str:item_type>/<int:item_id>/', views.remove_alert_mitre_attack, name='remove_alert_mitre_attack'),
    
    # MITRE ATT&CK Group routes
    path('mitre/groups/', views.mitre_attack_group_list, name='mitre_attack_group_list'),
    path('mitre/groups/create/', views.mitre_attack_group_create, name='mitre_attack_group_create'),
    path('mitre/groups/<int:group_id>/', views.mitre_attack_group_detail, name='mitre_attack_group_detail'),
    path('mitre/groups/<int:group_id>/edit/', views.mitre_attack_group_edit, name='mitre_attack_group_edit'),
    path('mitre/groups/<int:group_id>/delete/', views.mitre_attack_group_delete, name='mitre_attack_group_delete'),
    
    # MITRE ATT&CK Group association routes for cases
    path('case/<int:case_id>/mitre/group/add/', views.add_case_mitre_attack_group, name='add_case_mitre_attack_group'),
    path('case/<int:case_id>/mitre/group/remove/<int:group_id>/', views.remove_case_mitre_attack_group, name='remove_case_mitre_attack_group'),
    
    # MITRE ATT&CK Group association routes for alerts
    path('alert/<int:alert_id>/mitre/group/add/', views.add_alert_mitre_attack_group, name='add_alert_mitre_attack_group'),
    path('alert/<int:alert_id>/mitre/group/remove/<int:group_id>/', views.remove_alert_mitre_attack_group, name='remove_alert_mitre_attack_group'),
    
    # API endpoints para recuperar técnicas/subtécnicas por múltiplas táticas/técnicas
    path('api/tactics/multiple/techniques/', views.api_get_techniques_by_multiple_tactics, name='api_get_techniques_by_multiple_tactics'),
    path('api/techniques/multiple/subtechniques/', views.api_get_subtechniques_by_multiple_techniques, name='api_get_subtechniques_by_multiple_techniques'),
] 