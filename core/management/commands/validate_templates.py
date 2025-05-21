import os
import inspect
import importlib
from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver
from django.urls.resolvers import get_resolver
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.template.loader import get_template
from django.template.exceptions import TemplateDoesNotExist

class Command(BaseCommand):
    help = 'Validate that all views have corresponding templates'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Validating templates...'))
        
        # Get all URL patterns
        resolver = get_resolver()
        
        # Track results
        all_views = []
        missing_templates = []
        
        # Collect all views from URL patterns
        self.process_url_patterns(resolver.url_patterns, all_views)
        
        # Check templates for each view
        for view_info in all_views:
            view_class_or_func, view_kwargs = view_info
            
            # Skip admin views and function-based views without template_name
            if 'admin' in str(view_class_or_func):
                continue
                
            template_name = self.get_template_name(view_class_or_func, view_kwargs)
            
            if template_name:
                try:
                    get_template(template_name)
                    self.stdout.write(f"✅ Template found: {template_name}")
                except TemplateDoesNotExist:
                    missing_templates.append((view_class_or_func, template_name))
                    self.stdout.write(self.style.ERROR(f"❌ Missing template: {template_name} for view {view_class_or_func}"))
        
        # Show summary
        if missing_templates:
            self.stdout.write(self.style.ERROR(f"\nFound {len(missing_templates)} missing templates:"))
            for view, template in missing_templates:
                self.stdout.write(self.style.ERROR(f"- {template} for {view}"))
        else:
            self.stdout.write(self.style.SUCCESS("\nAll templates are in place!"))
    
    def process_url_patterns(self, url_patterns, result, prefix=''):
        """Process all URL patterns recursively."""
        for pattern in url_patterns:
            if isinstance(pattern, URLResolver):
                # If it's a resolver with included URL patterns, process them recursively
                self.process_url_patterns(pattern.url_patterns, result, prefix=prefix + pattern.pattern.regex.pattern)
            elif isinstance(pattern, URLPattern):
                # If it's a URL pattern with a view, add it to the results
                if hasattr(pattern.callback, 'view_class'):
                    # Class-based view
                    result.append((pattern.callback.view_class, getattr(pattern.callback, 'view_initkwargs', {})))
                else:
                    # Function-based view
                    result.append((pattern.callback, {}))
    
    def get_template_name(self, view, view_kwargs):
        """Get the template name for the given view."""
        # For class-based views that have template_name as a class attribute or instance attribute
        if inspect.isclass(view):
            # Check if it's a subclass of a view that uses templates
            if issubclass(view, (TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView)):
                # Check if template_name is in kwargs or view class attributes
                if 'template_name' in view_kwargs:
                    return view_kwargs['template_name']
                elif hasattr(view, 'template_name'):
                    return view.template_name
                
                # Try to guess the template name from the view name and the model
                if hasattr(view, 'model') and hasattr(view, '__name__'):
                    view_type = None
                    if issubclass(view, ListView):
                        view_type = '_list'
                    elif issubclass(view, DetailView):
                        view_type = '_detail'
                    elif issubclass(view, CreateView) or issubclass(view, UpdateView):
                        view_type = '_form'
                    elif issubclass(view, DeleteView):
                        view_type = '_confirm_delete'
                    
                    if view_type and hasattr(view.model, '_meta'):
                        app_label = view.model._meta.app_label
                        model_name = view.model._meta.model_name
                        return f"{app_label}/{model_name}{view_type}.html"
        
        # For function-based views, try to find template_name in the function code
        elif callable(view) and hasattr(view, '__code__'):
            try:
                # Try to inspect the function to find render calls
                source = inspect.getsource(view)
                
                # Simple pattern matching for common render patterns 
                # (this is not complete but catches the most common cases)
                if "render" in source:
                    # Look for patterns like render(request, 'template.html', ...)
                    import re
                    match = re.search(r"render\s*\(\s*\w+\s*,\s*['\"]([^'\"]+)['\"]", source)
                    if match:
                        return match.group(1)
            except (TypeError, OSError):
                # If we can't get the source code, just skip
                pass
        
        return None 