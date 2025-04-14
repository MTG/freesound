from django import template
from django.conf import settings

register = template.Library()


def bst_taxonomy_category_key_to_category_names(category_key):
    """
    Get the category names for the given category key.
    This includes both the top-level and the second-level category names.
    E.g.: "m-sp" -> ("Music", "Solo percussion"), "m" -> ("Music", None)
    """
    if category_key is None:
        return (None, None)
    if '-' in category_key:
        # Second-level category key
        top_level_key = category_key.split('-')[0]
        second_level_key = category_key
    else:
        # Only top-level category spcifcied, second-level is unknown
        top_level_key = category_key
        second_level_key = None
    try:
        top_level_category_name = settings.BROAD_SOUND_TAXONOMY[top_level_key]['name']
    except IndexError:
        # If for some reason we change category keys and some sounds are outdated, let's not crash
        top_level_category_name = None
    try:
        second_level_category_name = settings.BROAD_SOUND_TAXONOMY[second_level_key]['name'] if second_level_key is not None else None
    except IndexError:
        # If for some reason we change category keys and some sounds are outdated, let's not crash
        second_level_category_name = None
    return (top_level_category_name, second_level_category_name)

def bst_taxonomy_category_names_to_category_key(top_level_name, second_level_name):
    """
    Get the category key for the given category names.
    This is the reverse of bst_taxonomy_category_key_to_category_names.
    E.g.: ("Music", "Solo percussion") -> "m-sp", ("Music", None) -> "m"
    """
    if top_level_name is None:
        return None

    # Find the top-level key
    top_level_key = None
    for category_key, val in settings.BROAD_SOUND_TAXONOMY.items():
        if val.get("level") == 1 and val.get('name') == top_level_name:
            top_level_key = category_key
            break
    if top_level_key is None:
        return None

    if second_level_name is None:
        return top_level_key

    # Find second-level key under the correct top-level category
    for category_key, val in settings.BROAD_SOUND_TAXONOMY.items():
        if category_key.startswith(f"{top_level_key}-") and val.get('name') == second_level_name:
            return category_key

    # If no matching second-level category, return just the top-level key
    return top_level_key

@register.filter
def get_bst_taxonomy_top_level_category_key(value):
    """
    Extract the top level category key from the given value.
    The top level category is the part before the '-' in value.
    E.g.: "m-sp" -> "m"
    """
    return value.split('-')[0] if '-' in value else value

@register.filter
def get_bst_taxonomy_description(value):
    """
    Return BST taxonomy class description for a given taxonomy 
    cateogory/subcategory key.
    """
    return settings.BROAD_SOUND_TAXONOMY[value]['description'] 
