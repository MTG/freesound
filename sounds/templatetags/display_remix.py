'''
Created on May 6, 2011

@author: stelios
'''
from __future__ import absolute_import
from tags.models import TaggedItem as ti
from django.contrib.contenttypes.models import ContentType
from sounds.models import Sound
#avoid namespace clash with 'tags' templatetag
from django import template

register = template.Library()
@register.inclusion_tag('sounds/display_remix.html', takes_context=True)

def display_remix(context, sound):
    return '1'
