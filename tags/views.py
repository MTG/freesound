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

from tags.models import Tag, FS1Tag
from django.conf import settings
from django.urls import reverse
from django.http import Http404, HttpResponsePermanentRedirect
from django.shortcuts import render
from django.template import RequestContext
from utils.search.solr import SolrQuery, SolrResponseInterpreter, \
    SolrResponseInterpreterPaginator, SolrException, Solr
import logging
from follow import follow_utils
import sounds

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

    solr = Solr(settings.SOLR_URL)
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
        group_truncate=True)  # Sets how many results from the same grup are taken into account for computing the facets

    try:
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_PAGE)
        num_results = paginator.count
        non_grouped_number_of_results = results.non_grouped_number_of_matches
        page = paginator.page(current_page)
        error = False
        tags = [dict(name=f[0], count=f[1]) for f in results.facets["tag"]]

        docs = results.docs
        resultids = [d.get("id") for d in docs]
        resultsounds = sounds.models.Sound.objects.bulk_query_id(resultids)
        allsounds = {}
        for s in resultsounds:
            allsounds[s.id] = s
        for d in docs:
            d["sound"] = allsounds[d["id"]]

    except SolrException as e:
        error = True
        search_logger.error("SOLR ERROR - %s" % e)
    except :
        error = True

    slash_tag = "/".join(multiple_tags)
    space_tag = " ".join(multiple_tags)

    if slash_tag:
        follow_tags_url = reverse('follow-tags', args=[slash_tag])
        unfollow_tags_url = reverse('unfollow-tags', args=[slash_tag])
        show_unfollow_button = False
        if request.user.is_authenticated:
            show_unfollow_button = follow_utils.is_user_following_tag(request.user, slash_tag)

    return render(request, 'sounds/tags.html', locals())


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
