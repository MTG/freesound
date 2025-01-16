from django import template

register = template.Library()

@register.filter
def get_top_level_bst_category(value):
    """
    Extract the top level category from the given value.
    The top level category is the part before the '-' in value.
    """
    return value.split('-')[0] if '-' in value else value
