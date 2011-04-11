from django import template
from sounds.models import Sound

register = template.Library()

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound):
    if isinstance(sound, Sound):
        return {
                'sound_id': sound.id,
                'sound': [sound],
                'media_url': context['media_url'],
                'sounds_url': context['sounds_url']
                }        
    elif isinstance(sound, int):
        return {
                'sound_id': sound,
                'sound': Sound.objects.select_related('user').filter(id=sound), # need to use filter here because we don't want the query to be evaluated already!
                'media_url': context['media_url'],
                'sounds_url': context['sounds_url']
                }
    else:
        raise template.TemplateSyntaxError, "the display_sound tag needs either a sound id or an actual sound object"
