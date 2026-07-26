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

"""Server side of the sound grid editor (collection edit, pack edit).

The client (soundGridEditor.js) keeps the pending edits and re-fetches cards from a
``render-cards`` endpoint on every search / sort / page change, so all three happen here.
"""

from typing import NamedTuple

from django.shortcuts import render

from sounds.models import Sound
from utils.pagination import build_paginator_template_context, paginate
from utils.search.search_sounds import perform_search_engine_query


class SortOption(NamedTuple):
    label: str
    orm_field: str = ""  # only used by the public collection page
    needs_featured: bool = False  # only offered by grids that have featured sounds


FEATURED_SORT = "featured"
DEFAULT_SORT = "created_desc"

# FEATURED_SORT has no ORM field: it is ordered by the object's featured_sound_ids
SORT_OPTIONS = {
    FEATURED_SORT: SortOption("Featured first", needs_featured=True),
    DEFAULT_SORT: SortOption("Date added (newest first)", "-collectionsound__created"),
    "created_asc": SortOption("Date added (oldest first)", "collectionsound__created"),
    "name": SortOption("Name (A to Z)", "original_filename"),
}

# Safety bound on the pending delta, not a product limit (the forms enforce those)
MAX_PENDING_ADDED = 1000


def resolve_sort(request, has_featured=False):
    """Return ``(sort_options, sort_key)``, falling back to the default for unknown keys."""
    options = {key: option for key, option in SORT_OPTIONS.items() if has_featured or not option.needs_featured}
    default = FEATURED_SORT if has_featured else DEFAULT_SORT
    sort_key = request.GET.get("s") or default
    return options, sort_key if sort_key in options else default


def sorted_paginated_edit_sounds(request, saved_meta, addable_sounds_qs, per_page, featured_ids=None):
    """Merge the client's pending ``added`` delta into ``saved_meta``, then search/sort/paginate.

    ``saved_meta`` is ``[{"id","name","username","date_added"}]``; added ids are looked up in
    ``addable_sounds_qs`` (ineligible ones dropped). ``featured_ids`` is the saved featured order,
    or None for grids without featured sounds. Returns ``(page_sounds, tvars)``.
    """
    meta = {m["id"]: m for m in saved_meta}
    added = [int(x) for x in request.GET.get("added", "").split(",") if x.isdigit()][:MAX_PENDING_ADDED]
    new_added = [sid for sid in added if sid not in meta]
    if new_added:
        for row in addable_sounds_qs.filter(id__in=new_added).values(
            "id", "original_filename", "user__username", "created"
        ):
            meta[row["id"]] = {
                "id": row["id"],
                "name": row["original_filename"],
                "username": row["user__username"],
                "date_added": row["created"],
            }

    ids = list(meta.keys())  # removed sounds stay in and are marked client-side
    is_empty = not ids

    search = request.GET.get("q", "").strip()
    if search:
        q = search.lower()
        ids = [i for i in ids if q in meta[i]["name"].lower() or q in meta[i]["username"].lower()]

    has_featured = featured_ids is not None
    _, sort_key = resolve_sort(request, has_featured=has_featured)
    if sort_key == FEATURED_SORT:
        # Client's pending featured order when sent, else the saved one
        featured_param = request.GET.get("featured")
        featured_order = (
            [int(x) for x in featured_param.split(",") if x.isdigit()]
            if featured_param is not None
            else list(featured_ids)
        )
        pos = {sid: i for i, sid in enumerate(featured_order)}
        ids.sort(key=lambda i: (pos.get(i, len(pos)), meta[i]["date_added"]))
    elif sort_key == "name":
        ids.sort(key=lambda i: meta[i]["name"].lower())
    else:
        ids.sort(key=lambda i: meta[i]["date_added"], reverse=sort_key == "created_desc")

    pagination = paginate(request, ids, per_page)
    page_ids = list(pagination["page"])
    sounds_by_id = {s.id: s for s in Sound.objects.bulk_query_id_public(page_ids)} if page_ids else {}
    sounds = [sounds_by_id[i] for i in page_ids if i in sounds_by_id]

    tvars = build_paginator_template_context(pagination["page"], base_path=request.path, base_query=request.GET)
    tvars.update(
        {"is_empty": is_empty, "total": len(meta), "show_featured": has_featured, "current_search": search}
    )
    return sounds, tvars


def render_edit_cards(request, sounds, extra_tvars):
    return render(request, "sounds/edit_sound_cards.html", {"sounds": sounds, **extra_tvars})


def add_sounds_modal_helper(request, username=None, exclude_sound_ids=None):
    """``exclude_sound_ids`` are the already-saved sounds; the client only sends its pending additions."""
    query = request.GET.get("q")
    tvars = {"sounds_to_select": [], "q": query or "", "search_executed": query is not None}
    if query is None or (query == "" and username is None):
        return tvars

    exclude_ids = set(exclude_sound_ids or [])
    exclude_ids.update(int(i) for i in request.GET.get("exclude", "").split(",") if i.isdigit())
    filter_parts = []
    if username is not None:
        filter_parts.append(f"username:{username}")
    if exclude_ids:
        # Multi-value "-id:(1 2 3)" instead of NOT (id:1 OR id:2 OR ...): same semantics, shorter query
        filter_parts.append("-id:(" + " ".join(str(i) for i in exclude_ids) + ")")

    results, _ = perform_search_engine_query(
        {"textual_query": query, "query_filter": " AND ".join(filter_parts), "num_sounds": 9}
    )
    tvars["sounds_to_select"] = [doc["id"] for doc in results.docs]
    return tvars
