"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from accounts.views import login_view, logout_view, dashboard, UserListView, UserDetailView, UserCreateView, UserUpdateView
from organizations.views import (
    OrganizationListView, OrganizationDetailView, OrganizationCreateView,
    OrganizationUpdateView, OrganizationDeleteView
)
from alerts.views import (
    AlertListView, AlertDetailView, AlertCreateView, AlertUpdateView, AlertDeleteView,
    escalate_to_case
)
from cases.views import (
    CaseListView, CaseDetailView, CaseCreateView, CaseUpdateView, CaseDeleteView,
    add_case_comment, add_case_attachment, delete_case_attachment, add_case_event
)
from core.views import home, handler404, handler500

# Custom 404 and 500 handlers
handler404 = handler404
handler500 = handler500

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Core URLs
    path('', home, name='home'),
    
    # Authentication URLs
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # User management URLs
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/update/', UserUpdateView.as_view(), name='user_update'),
    
    # Organization URLs
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('organizations/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('organizations/create/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/<int:pk>/update/', OrganizationUpdateView.as_view(), name='organization_update'),
    path('organizations/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization_delete'),
    
    # Alert URLs
    path('alerts/', AlertListView.as_view(), name='alert_list'),
    path('alerts/<int:pk>/', AlertDetailView.as_view(), name='alert_detail'),
    path('alerts/create/', AlertCreateView.as_view(), name='alert_create'),
    path('alerts/<int:pk>/update/', AlertUpdateView.as_view(), name='alert_update'),
    path('alerts/<int:pk>/delete/', AlertDeleteView.as_view(), name='alert_delete'),
    path('alerts/<int:pk>/escalate/', escalate_to_case, name='escalate_to_case'),
    
    # Case URLs
    path('cases/', CaseListView.as_view(), name='case_list'),
    path('cases/<int:pk>/', CaseDetailView.as_view(), name='case_detail'),
    path('cases/create/', CaseCreateView.as_view(), name='case_create'),
    path('cases/<int:pk>/update/', CaseUpdateView.as_view(), name='case_update'),
    path('cases/<int:pk>/delete/', CaseDeleteView.as_view(), name='case_delete'),
    path('cases/<int:pk>/comment/', add_case_comment, name='add_case_comment'),
    path('cases/<int:pk>/attachment/', add_case_attachment, name='add_case_attachment'),
    path('cases/attachments/<int:pk>/delete/', delete_case_attachment, name='delete_case_attachment'),
    path('cases/<int:pk>/timeline/event/', add_case_event, name='add_case_event'),
    
    # Include core app URLs
    path('', include('core.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
