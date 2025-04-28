from django.shortcuts import render
from django.views.generic import TemplateView


class HomePageView(TemplateView):
    """Home page view for the application."""

    template_name = "index.html"
