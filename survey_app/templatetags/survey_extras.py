from django import template
from django.template.defaultfilters import floatformat

register = template.Library()

@register.filter
def index(list_obj, i):
    try:
        return list_obj[i]
    except:
        return None

@register.filter
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire par sa clé"""
    return dictionary.get(key)

@register.filter
def sum_counts(queryset):
    """Calcule la somme des comptages dans un queryset"""
    return sum(item['count'] for item in queryset)

@register.filter
def percentage(value, total):
    """Calcule le pourcentage d'une valeur par rapport à un total"""
    try:
        return floatformat((value / total) * 100, 1)
    except (ValueError, ZeroDivisionError):
        return 0 