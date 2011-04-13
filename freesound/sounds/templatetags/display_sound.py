from __future__ import absolute_import
from tags.models import TaggedItem as ti 
#avoid namespace clash with 'tags' templatetag

from django import template
from sounds.models import Sound

register = template.Library()
@register.inclusion_tag('sounds/display_sound.html', takes_context=True)

def display_sound(context, sound):
    if isinstance(sound, Sound):
        return {
                'sound_id': sound.id,
                'sound': [sound],
                'sound_tags':ti.objects.select_related().filter(object_id=sound.id, content_type=18).all(),
                'media_url': context['media_url'],
                'sounds_url': context['sounds_url']
                }        
    elif isinstance(sound, int):
        return {
                'sound_id': sound,
                'sound': Sound.objects.select_related('user').filter(id=sound), # need to use filter here because we don't want the query to be evaluated already!
                'sound_tags':ti.objects.select_related().filter(object_id=sound, content_type=18).all(),
                'media_url': context['media_url'],
                'sounds_url': context['sounds_url']
                }
    else:
        raise template.TemplateSyntaxError, "the display_sound tag needs either a sound id or an actual sound object"
