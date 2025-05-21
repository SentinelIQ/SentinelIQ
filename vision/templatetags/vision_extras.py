from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def split(value, arg):
    """
    Divide uma string pelo separador especificado.
    
    Exemplo:
        {{ "tag1,tag2,tag3"|split:"," }}
    """
    if not value:
        return []
    return [x.strip() for x in value.split(arg)]


@register.filter
def tlp_badge(tlp_level):
    """
    Retorna um badge HTML para o nível TLP.
    
    Exemplo:
        {{ item.tlp|tlp_badge }}
    """
    if tlp_level == 'white':
        return mark_safe('<span class="badge bg-light text-dark">TLP:WHITE</span>')
    elif tlp_level == 'green':
        return mark_safe('<span class="badge bg-success">TLP:GREEN</span>')
    elif tlp_level == 'amber':
        return mark_safe('<span class="badge bg-warning text-dark">TLP:AMBER</span>')
    elif tlp_level == 'red':
        return mark_safe('<span class="badge bg-danger">TLP:RED</span>')
    return mark_safe('<span class="badge bg-secondary">TLP:UNKNOWN</span>')


@register.filter
def confidence_badge(confidence_level):
    """
    Retorna um badge HTML para o nível de confiança.
    
    Exemplo:
        {{ item.confidence|confidence_badge }}
    """
    if confidence_level == 'high':
        return mark_safe('<span class="badge bg-danger">High</span>')
    elif confidence_level == 'medium':
        return mark_safe('<span class="badge bg-warning text-dark">Medium</span>')
    elif confidence_level == 'low':
        return mark_safe('<span class="badge bg-info">Low</span>')
    return mark_safe('<span class="badge bg-secondary">Unknown</span>') 