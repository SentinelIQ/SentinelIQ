from django.urls import path
from . import views

app_name = 'vision'

urlpatterns = [
    # Feeds e listagem geral
    path('feeds/', views.FeedListView.as_view(), name='feed_list'),
    path('search/', views.ThreatIntelligenceSearchView.as_view(), name='search'),
    
    # MISP Integration
    path('misp/new/', views.MISPInstanceCreateView.as_view(), name='misp_create'),
    path('misp/<int:pk>/', views.MISPInstanceDetailView.as_view(), name='misp_detail'),
    path('misp/<int:pk>/edit/', views.MISPInstanceUpdateView.as_view(), name='misp_edit'),
    path('misp/<int:pk>/sync/', views.sync_misp_instance, name='misp_sync'),
    path('misp/test-connection/', views.test_misp_connection, name='test_misp_connection'),
    path('misp/<int:pk>/delete/', views.MISPInstanceDeleteView.as_view(), name='misp_delete'),
    
    # MISP-Case Integration
    path('create-case/<int:pk>/', views.create_case_from_threat_intel, name='create_case_from_intel'),
    path('enrich-case/<int:case_pk>/', views.enrich_case_with_threat_intel, name='enrich_case'),
    path('threat-intel-match/<int:observable_pk>/', views.threat_intel_match, name='threat_intel_match'),
] 