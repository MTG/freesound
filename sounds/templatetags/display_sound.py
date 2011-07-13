from __future__ import absolute_import
#avoid namespace clash with 'tags' templatetag
from tags.models import TaggedItem as ti
from django.contrib.contenttypes.models import ContentType
from sounds.models import Sound
from django import template

register = template.Library()
sound_content_type = ContentType.objects.get_for_model(Sound)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound):

    if isinstance(sound, Sound):
        sound_id = sound.id
        sound_obj = [sound]
    else:
        sound_id = int(sound)
        try:
            #sound_obj = Sound.objects.get(id=sound_id)
            sound_obj = Sound.objects.select_related().filter(id=sound) # need to use filter here because we don't want the query to be evaluated already!
        except Sound.DoesNotExist:
            sound_obj = []

    return { 'sound_id':     sound_id,
             'sound':        sound_obj,
             'sound_tags':   sound_obj[0].tags.select_related().all(),
             'media_url':    context['media_url'],
             'request':      context['request']
           }
