from django import template
from sounds.models import Sound
from utils.tags import annotate_tags

register = template.Library()

@register.filter
def add_sizes(tags, arguments):
    sort, small_size, large_size = arguments.split(":")
    return annotate_tags(tags, sort.lower() == "true", float(small_size), float(large_size))

@register.filter
def join_tags_except(list, exclude):
    return "/".join(sorted(filter(lambda x: x != exclude, list))) if list else None