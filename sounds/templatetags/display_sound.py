from __future__ import absolute_import
from tags.models import TaggedItem as ti 
from django.contrib.contenttypes.models import ContentType
from sounds.models import Sound
#avoid namespace clash with 'tags' templatetag
from django import template

register = template.Library()
@register.inclusion_tag('sounds/display_sound.html', takes_context=True)

def display_sound(context, sound):
    
    if isinstance(sound, Sound):
        return {
                'sound_id': sound.id,
                'sound': [sound],
                'sound_tags':ti.objects.select_related().filter(object_id=sound.id, content_type=ContentType.objects.get_for_model(Sound)).all(),
                'media_url': context['media_url']
                }        
    else:
        return {
                'sound_id': int(sound),
                'sound': Sound.objects.select_related('user').filter(id=sound), # need to use filter here because we don't want the query to be evaluated already!
                'sound_tags':ti.objects.select_related().filter(object_id=sound, content_type=ContentType.objects.get_for_model(Sound)).all(),
                'media_url': context['media_url']
                }