from django import template
from django.conf import settings

register = template.Library()


def bst_taxonomy_category_key_to_category_names(category_key):
    """
    Get the category names for the given category key.
    This includes both the top level and the sub level category names.
    E.g.: "m-sp" -> ("Music", "Solo percussion"), "m" -> ("Music", None)
    """
    if '-' in category_key:
        # Sub level category key
        top_level_key = category_key.split('-')[0]
        second_level_key = category_key
    else:
        # Only top level category spcifcied, sub level is unknown
        top_level_key = category_key
        second_level_key = None
    try:
        top_level_category_name = [item['name'] for item in settings.BROAD_SOUND_TAXONOMY if item['key'] == top_level_key][0]
    except IndexError:
        # If for some reason we change category keys and some sounds are outdated, let's not crash
        top_level_category_name = None
    try:
        second_level_category_name = [item['name'] for item in settings.BROAD_SOUND_TAXONOMY if item['key'] == second_level_key][0] \
            if second_level_key is not None else None
    except IndexError:
        # If for some reason we change category keys and some sounds are outdated, let's not crash
        second_level_category_name = None
    return (top_level_category_name, second_level_category_name)


@register.filter
def get_bst_taxonomy_top_level_category_key(value):
    """
    Extract the top level category key from the given value.
    The top level category is the part before the '-' in value.
    E.g.: "m-sp" -> "m"
    """
    return value.split('-')[0] if '-' in value else value
