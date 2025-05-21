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
    
    # Include app URLs
    path('alerts/', include('alerts.urls')),
    path('cases/', include('cases.urls')),
    path('', include('core.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
