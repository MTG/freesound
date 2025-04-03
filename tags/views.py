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
from django.core.cache import cache
from django.http import Http404, HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
import sentry_sdk

from search.views import search_view_helper
from tags.models import Tag, FS1Tag
from utils.search import SearchEngineException
from utils.search.search_sounds import perform_search_engine_query

search_logger = logging.getLogger("search")


def tags(request):
    # Share same view code as for the search view, but "tags mode" will be on
    tvars = search_view_helper(request)

    # If there are no tags in filter, get display initial tag cloud
    if 'sqp' in tvars and not tvars["sqp"].get_tags_in_filters():
        return tag_cloud(request)

    return render(request, "search/search.html", tvars)


def tag_cloud(request):
    tvars = {}
    initial_tagcloud = cache.get("initial_tagcloud")
    if initial_tagcloud is None:
        try:
            # If tagcloud is not cached, make a query to retrieve it and save it to cache
            results, _ = perform_search_engine_query(
                dict(
                    textual_query="",
                    query_filter="*:*",
                    num_sounds=1,
                    facets={settings.SEARCH_SOUNDS_FIELD_TAGS: {"limit": 200}},
                    group_by_pack=True,
                    group_counts_as_one_in_facets=False,
                )
            )
        except SearchEngineException as e:
            search_logger.info(f"Tag browse error: Could probably not connect to Solr - {e}")
            # Manually capture exception so it has more info and Sentry can organize it properly
            sentry_sdk.capture_exception(e)
            tvars.update({"error_text": "The search server could not be reached, please try again later."})
        else:
            if settings.SEARCH_SOUNDS_FIELD_TAGS in results.facets:
                initial_tagcloud = [
                    dict(name=f[0], count=f[1], browse_url=reverse("tags", args=[f[0]]))
                    for f in results.facets.get(settings.SEARCH_SOUNDS_FIELD_TAGS, [])
                ]
                cache.set("initial_tagcloud", initial_tagcloud, 60 * 60 * 12)  # cache for 12 hours
                tvars.update({"initial_tagcloud": initial_tagcloud})
            else:
                tvars.update({"error_text": "There was an error while loading results, please try again later."})
    else:
        tvars.update({"initial_tagcloud": initial_tagcloud})

    return render(request, "tags/tag_cloud.html", tvars)


def multiple_tags_lookup(request, multiple_tags):
    multiple_tags = multiple_tags.split("/")

    # Make all tags lower-cased and unique to get a case-insensitive search filter and shortened browse url
    multiple_tags = sorted({x.lower() for x in multiple_tags if x})
    # We re-write tags as query filter and redirect
    search_filter = "+".join('tag:"' + tag + '"' for tag in multiple_tags)
    username_flt = request.GET.get("username_flt", None)
    if username_flt is not None:
        # If username is passed as a GET parameter, add it as well to the filter
        search_filter += f"+username:{username_flt}"
    pack_flt = request.GET.get("pack_flt", None)
    if pack_flt is not None:
        # If username is passed as a GET parameter, add it as well to the filter
        search_filter += f"+grouping_pack:{pack_flt}"

    return HttpResponseRedirect(f"{reverse('tags')}?f={search_filter}")


def old_tag_link_redirect(request):
    fs1tag_id = request.GET.get("id", False)
    if fs1tag_id:
        tags = fs1tag_id.split("_")
        try:
            fs1tags = FS1Tag.objects.filter(fs1_id__in=tags).values_list("tag", flat=True)
        except ValueError:
            raise Http404

        tags = Tag.objects.filter(id__in=fs1tags).values_list("name", flat=True)
        if not tags:
            raise Http404

        return HttpResponsePermanentRedirect(reverse("tags", args=["/".join(tags)]))
    else:
        raise Http404
