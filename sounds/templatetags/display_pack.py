#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


from django import template

from sounds.models import Pack

register = template.Library()


@register.inclusion_tag('sounds/display_pack.html', takes_context=True)
def display_pack(context, pack, size='small', show_bookmark_similarity_buttons=True):
    """This templatetag is used to display a pack with some randomly selected sound players.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        pack (int or Pack): pack ID or Pack object of the pack that will be shown. If no pack exists for the
          given ID, the display_pack.html will be rendered with empty HTML.
        size (str, optional): size of the "info" to display. This parameter only applies to BW interface.
          Must be one of ['small' (default), 'big']. Information about the contents of each
          size is given in the display_pack.html template code.

    Returns:
        dict: dictionary with the variables needed for rendering the pack with the display_pack.html template

    """
    if not isinstance(pack, Pack):
        try:
            # use filter here instead of get because we don't want the query to be evaluated before rendering the
            # template as this would bypass the html cache in the template
            pack = Pack.objects.bulk_query_id([int(pack)])[0]
        except ValueError:
            pack = None
        except Pack.DoesNotExist:
            pack = None

    request = context.get('request')

    # Add 'request' to the returned context dictionary below so when the display_sound templatetag is called inside
    # display_pack templatetag it is given request in the context as well.
    return {
        'pack': pack,
        'size': size,
        'request': request,
        'show_bookmark_similarity_buttons': show_bookmark_similarity_buttons,
    }


@register.inclusion_tag('sounds/display_pack.html', takes_context=True)
def display_pack_small_no_bookmark(context, pack):
    return display_pack(context, pack, size='small', show_bookmark_similarity_buttons=False)


@register.inclusion_tag('sounds/display_pack.html', takes_context=True)
def display_pack_big(context, pack):
    return display_pack(context, pack, size='big')


@register.inclusion_tag('sounds/display_pack_selectable.html', takes_context=True)
def display_pack_small_selectable(context, pack, selected=False):
    context = context.get('original_context', context)  # This is to allow passing context in nested inclusion tags
    tvars = display_pack(context, pack, size='small')
    tvars.update({
        'selected': selected,
    })
    return tvars