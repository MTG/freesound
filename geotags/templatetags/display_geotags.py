'''
Created on Nov 3, 2011

@author: groma
'''
from django import template

register = template.Library()

@register.inclusion_tag('geotags/display_geotags.html', takes_context=True)
def display_geotags(context):
    return {"media_url": context['media_url']}