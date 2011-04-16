'''
Created on Apr 16, 2011

@author: stelios
'''
from django import template
from django.conf import settings

register = template.Library()

@register.inclusion_tag('templatetags/google_analytics.html')
def google_analytics():
    return {'google_analytics_key' : settings.GOOGLE_ANALYTICS_KEY}
    