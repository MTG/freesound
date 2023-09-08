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

from django.conf import settings
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import render
from django.urls import Resolver404, reverse

import sounds.models
from follow import follow_utils
from search.views import search_view_helper_form
from tags.models import Tag, FS1Tag
from utils.frontend_handling import render, using_beastwhoosh
from utils.search import SearchEngineException
from utils.search.search_sounds import perform_search_engine_query

search_logger = logging.getLogger("search")


def tags(request, multiple_tags=None):

    if multiple_tags:
        multiple_tags = multiple_tags.split('/')
    else:
        multiple_tags = []
    multiple_tags = sorted([x for x in multiple_tags if x])

    if using_beastwhoosh(request):
        if multiple_tags:
            # If using BW and tags in URL, we re-write tags as query filter and redirect
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
            tvars = search_view_helper_form(request, tags_mode=True)
            return render(request, 'search/search.html', tvars)

    # NOTE: all code below will not be used when NG UI is retired as tags page is calcualted using search views

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    page = None
    tags = []
    error = False
    docs = {}
    non_grouped_number_of_results = 0
    paginator = None
    try:
        if multiple_tags:
            query_filter = " ".join("tag:\"" + tag + "\"" for tag in multiple_tags)
        else:
            query_filter = "*:*"

        results, paginator = perform_search_engine_query(dict(
            textual_query='',
            query_filter=query_filter,
            offset=(current_page- 1) * settings.SOUNDS_PER_PAGE,
            num_sounds=settings.SOUNDS_PER_PAGE,
            sort=settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST,
            group_by_pack=True,
            facets={settings.SEARCH_SOUNDS_FIELD_TAGS: {'limit': 100}},
            group_counts_as_one_in_facets=False,
        ))

        page = paginator.page(current_page)
        non_grouped_number_of_results = results.non_grouped_number_of_results
        facets = results.facets
        docs = results.docs

        tags = [dict(name=f[0], count=f[1]) for f in facets["tag"]]
        resultids = [d.get("id") for d in docs]
        resultsounds = sounds.models.Sound.objects.bulk_query_id(resultids)
        allsounds = {}
        for s in resultsounds:
            allsounds[s.id] = s
        for d in docs:
            d["sound"] = allsounds[d["id"]]

    except SearchEngineException as e:
        error = True
        search_logger.error(f'Search error: {e}')
    except Exception as e:
        error = True
        search_logger.error(f'Could probably not connect to Solr - {e}')

    # Calculate follow_tags_url, unfollow_tags_url and show_unfollow_button tvars
    slash_tag = "/".join(multiple_tags)
    follow_tags_url = ''
    unfollow_tags_url = ''
    show_unfollow_button = False
    if slash_tag:
        follow_tags_url = reverse('follow-tags', args=[slash_tag])
        unfollow_tags_url = reverse('unfollow-tags', args=[slash_tag])
        show_unfollow_button = False

        if request.user.is_authenticated:
            show_unfollow_button = follow_utils.is_user_following_tag(request.user, slash_tag)

    tvars = {'show_unfollow_button': show_unfollow_button,
             'multiple_tags': multiple_tags,
             'follow_tags_url': follow_tags_url,
             'unfollow_tags_url': unfollow_tags_url,
             'error': error,
             'tags': tags,
             'slash_tag': slash_tag,
             'non_grouped_number_of_results': non_grouped_number_of_results,
             'docs': docs,
             'paginator': paginator,
             'page': page,
             'current_page': current_page
             }
    return render(request, 'sounds/tags.html', tvars)


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
