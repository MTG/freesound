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
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.urls import reverse

import sounds.models
from follow import follow_utils
from search.views import perform_solr_query
from tags.models import Tag, FS1Tag
from utils.search.solr import SolrQuery, SolrException, Solr

search_logger = logging.getLogger("search")


def tags(request, multiple_tags=None):

    if multiple_tags:
        multiple_tags = multiple_tags.split('/')
    else:
        multiple_tags = []

    multiple_tags = sorted(filter(lambda x: x, multiple_tags))

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    query = SolrQuery()
    if multiple_tags:
        query.set_query(" ".join("tag:\"" + tag + "\"" for tag in multiple_tags))
    else:
        query.set_query("*:*")
    query.set_query_options(start=(current_page - 1) * settings.SOUNDS_PER_PAGE, rows=settings.SOUNDS_PER_PAGE, field_list=["id"], sort=["num_downloads desc"])
    query.add_facet_fields("tag")
    query.set_facet_options_default(limit=100, sort=True, mincount=1, count_missing=False)
    query.set_group_field(group_field="grouping_pack")
    query.set_group_options(group_func=None,
                            group_query=None,
                            group_rows=10,
                            group_start=0,
                            group_limit=1,
                            group_offset=0,
                            group_sort=None,
                            group_sort_ingroup=None,
                            group_format='grouped',
                            group_main=False,
                            group_num_groups=True,
                            group_cache_percent=0,
                            group_truncate=True)  # Sets how many results from the same group are taken into account for computing the facets

    page = None
    tags = []
    error = False
    docs = {}
    non_grouped_number_of_results = 0
    paginator = None
    try:
        non_grouped_number_of_results, facets, paginator, page, docs = perform_solr_query(query, current_page)
        tags = [dict(name=f[0], count=f[1]) for f in facets["tag"]]
        resultids = [d.get("id") for d in docs]
        resultsounds = sounds.models.Sound.objects.bulk_query_id(resultids)
        allsounds = {}
        for s in resultsounds:
            allsounds[s.id] = s
        for d in docs:
            d["sound"] = allsounds[d["id"]]

    except SolrException as e:
        error = True
        search_logger.warning('Search error: query: %s error %s' % (query, e))
    except Exception as e:
        error = True
        search_logger.error('Could probably not connect to Solr - %s' % e)

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
