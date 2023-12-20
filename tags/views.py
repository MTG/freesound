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

import logging

from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from search.views import search_view_helper
from tags.models import Tag, FS1Tag

search_logger = logging.getLogger("search")


def tags(request, multiple_tags=None):

    if multiple_tags:
        multiple_tags = multiple_tags.split('/')
    else:
        multiple_tags = []
    multiple_tags = sorted([x for x in multiple_tags if x])
    if multiple_tags:
        # We re-write tags as query filter and redirect
        search_filter = "+".join('tag:"' + tag + '"' for tag in multiple_tags)
        username_flt = request.GET.get('username_flt', None)
        if username_flt is not None:
            # If username is passed as a GET parameter, add it as well to the filter
            search_filter += f'+username:{username_flt}'
        pack_flt = request.GET.get('pack_flt', None)
        if pack_flt is not None:
            # If username is passed as a GET parameter, add it as well to the filter
            search_filter += f'+grouping_pack:{pack_flt}'

        return HttpResponseRedirect(f"{reverse('tags')}?f={search_filter}")
    else:
        # Share same view code as for the search view, but set "tags mode" on
        tvars = search_view_helper(request, tags_mode=True)
        return render(request, 'search/search.html', tvars)


def old_tag_link_redirect(request):
    fs1tag_id = request.GET.get('id', False)
    if fs1tag_id:
        tags = fs1tag_id.split('_')
        try:
            fs1tags = FS1Tag.objects.filter(fs1_id__in=tags).values_list('tag', flat=True)
        except ValueError as e:
            raise Http404

        tags = Tag.objects.filter(id__in=fs1tags).values_list('name', flat=True)
        if not tags:
            raise Http404

        return HttpResponsePermanentRedirect(reverse("tags", args=['/'.join(tags)]))
    else:
        raise Http404
