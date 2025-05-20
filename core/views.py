from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _


def home(request):
    """Home page view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def handler404(request, exception):
    """404 error handler"""
    return render(request, 'core/404.html', status=404)


def handler500(request):
    """500 error handler"""
    return render(request, 'core/500.html', status=500)
