from django.urls import path
from . import views

app_name = 'organizations'

urlpatterns = [
    path('', views.OrganizationListView.as_view(), name='organization_list'),
    path('<int:pk>/', views.OrganizationDetailView.as_view(), name='organization_detail'),
    path('create/', views.OrganizationCreateView.as_view(), name='organization_create'),
    path('<int:pk>/update/', views.OrganizationUpdateView.as_view(), name='organization_update'),
    path('<int:pk>/delete/', views.OrganizationDeleteView.as_view(), name='organization_delete'),
] 