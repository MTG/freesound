from __future__ import absolute_import
from sounds.models import Pack
from django import template

register = template.Library()

@register.inclusion_tag('sounds/display_pack.html', takes_context=True)
def display_pack(context, pack):

    if isinstance(pack, Pack):
        pack_id = pack.id
        pack_obj = [pack]
    else:
        pack_id = int(pack)
        try:
            #sound_obj = Sound.objects.get(id=sound_id)
            pack_obj = Pack.objects.select_related('username').filter(id=pack) # need to use filter here because we don't want the query to be evaluated already!
        except Pack.DoesNotExist:
            pack_obj = []

    return { 'pack_id':     pack_id,
             'pack':        pack_obj,
             'media_url':    context['media_url'],
           }
