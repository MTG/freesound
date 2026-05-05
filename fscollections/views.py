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

from functools import wraps
from operator import itemgetter
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Case, IntegerField, Q, Value, When
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from fscollections.forms import (
    CollectionEditForm,
    CollectionEditFormAsMaintainer,
    CreateCollectionForm,
    MaintainerForm,
    SelectCollectionOrNewCollectionForm,
)
from fscollections.models import Collection, CollectionDownload, CollectionDownloadSound, CollectionSound
from sounds.models import Sound
from sounds.views import add_sounds_modal_helper
from utils.downloads import download_sounds
from utils.pagination import build_paginator_template_context, paginate


def resolve_collection_from_url(view_func):
    """Fetches collection, redirects to canonical URL if name doesn't match, passes collection to view."""

    @wraps(view_func)
    def _wrapped_view(request, collection_id, collection_name, *args, **kwargs):
        collection = get_object_or_404(Collection, id=collection_id)
        expected_name = collection.url_kwargs["collection_name"]
        if collection_name != expected_name:
            url_name = request.resolver_match.url_name
            canonical_url = collection.get_url(url_name)
            query_params = request.GET.urlencode()
            if query_params:
                canonical_url = f"{canonical_url}?{query_params}"
            return HttpResponseRedirect(canonical_url)
        return view_func(request, collection, *args, **kwargs)

    return _wrapped_view


@login_required
@resolve_collection_from_url
def collection(request, collection):
    user = request.user
    is_maintainer = collection.maintainers.filter(username=user.username).exists()
    is_owner = user == collection.user
    maintainers = collection.maintainers.all()

    sort_key = request.GET.get("s") or settings.COLLECTION_SORT_DEFAULT
    if sort_key not in settings.COLLECTION_SORT_OPTIONS:
        sort_key = settings.COLLECTION_SORT_DEFAULT
    search = request.GET.get("q", "").strip()

    sounds = Sound.objects.bulk_sounds_for_collection(collection.id)
    if search:
        sounds = sounds.filter(Q(original_filename__icontains=search) | Q(user__username__icontains=search))

    if sort_key == "featured":
        featured_ids = list(collection.featured_sound_ids or [])
        if featured_ids:
            ordering = Case(
                *[When(id=sid, then=Value(i)) for i, sid in enumerate(featured_ids)],
                default=Value(len(featured_ids)),
                output_field=IntegerField(),
            )
            sounds = sounds.order_by(ordering, "collectionsound__created")
        else:
            sounds = sounds.order_by("collectionsound__created")
    else:
        _, sort_field = settings.COLLECTION_SORT_OPTIONS[sort_key]
        sounds = sounds.order_by(sort_field)

    pagination = paginate(request, sounds, settings.BOOKMARKS_PER_PAGE)
    page_sounds = list(pagination["page"])

    tvars = {
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "maintainers": maintainers,
        "sort_options": settings.COLLECTION_SORT_OPTIONS,
        "page_sounds": page_sounds,
        "featured_sound_ids_set": set(collection.featured_sound_ids or []),
        "current_sort": sort_key,
        "current_search": search,
    }
    tvars.update(pagination)
    return render(request, "collections/collection.html", tvars)


@login_required
def collections_for_user(request):
    user = request.user
    user_collections = Collection.objects.filter(user=user).order_by("-modified")
    maintainer_collections = Collection.objects.filter(maintainers__id=user.id).order_by("-modified")
    tvars = {"user_collections": user_collections, "maintainer_collections": maintainer_collections}
    # one URL needed to display all collections and one URL to display ONE collection at a time
    # the collections_for_user can be reused to display ONE collection so give it a thought on full collections display
    return render(request, "collections/your_collections.html", tvars)


@login_required
@resolve_collection_from_url
def collection_stats_section(request, collection):
    # TODO: this tries to imitate the pack_stats_section behaviour despite a lack of comprehension
    # on cache behaviour, so the stats shown by this are not properly updated
    if not request.GET.get("ajax"):
        return HttpResponseRedirect(reverse("your-collections"))
    tvars = {"collection": collection}
    return render(request, "collections/collection_stats_section.html", tvars)


@login_required
def add_sound_to_collection(request, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    msg_to_return = ""
    user_collections = Collection.objects.filter(Q(user=request.user) | Q(maintainers=request.user))
    user_collections = user_collections.distinct().order_by("modified")
    last_collection = user_collections.last()

    if not request.GET.get("ajax"):
        HttpResponseRedirect(reverse("sound", args=[sound.user.username, sound.id]))

    if request.method == "POST":
        form = SelectCollectionOrNewCollectionForm(
            request.POST, sound_id=sound_id, user_collections=user_collections, user_saving_sound=request.user
        )
        if form.is_valid():
            saved_collection = form.save()
            msg_to_return = f'Sound "{sound.original_filename}" saved under collection {saved_collection.name}'
            return JsonResponse({"success": True, "message": msg_to_return})
        else:
            msg_to_return = "You don't have permissions to add sounds to this collection."
            return JsonResponse({"success": False, "message": msg_to_return})
    else:
        form = SelectCollectionOrNewCollectionForm(
            initial={
                "collection": last_collection.id
                if last_collection
                else SelectCollectionOrNewCollectionForm.BOOKMARK_COLLECTION_CHOICE_VALUE
            },
            sound_id=sound.id,
            user_collections=user_collections,
            user_saving_sound=request.user,
        )
    collections_already_containing_sound = user_collections.filter(sounds__id=sound.id).distinct()
    full_collections = Collection.objects.filter(num_sounds__gte=settings.MAX_SOUNDS_PER_COLLECTION)
    tvars = {
        "user": request.user,
        "sound": sound,
        "sound_is_moderated_and_processed_ok": sound.moderated_and_processed_ok,
        "form": form,
        "collections_with_sound": collections_already_containing_sound,
        "full_collections": full_collections,
        "max_sounds_per_collection": settings.MAX_SOUNDS_PER_COLLECTION,
    }

    return render(request, "collections/modal_add_sound_to_collection.html", tvars)


@login_required
def create_collection(request):
    if not request.GET.get("ajax"):
        return HttpResponseRedirect(reverse("your-collections"))
    if request.method == "POST":
        form = CreateCollectionForm(request.POST, user=request.user)
        if form.is_valid():
            Collection.objects.create(
                user=request.user, name=form.cleaned_data["name"], description=form.cleaned_data["description"]
            )
            return JsonResponse({"success": True})
    else:
        form = CreateCollectionForm(user=request.user)
    tvars = {"form": form}
    return render(request, "collections/modal_create_collection.html", tvars)


@login_required
@resolve_collection_from_url
def delete_collection(request, collection):
    if request.method == "POST" and request.user == collection.user:
        msg = f"Collection {collection.name} successfully deleted."
        collection.delete()
        messages.add_message(request, messages.WARNING, msg)
        return HttpResponseRedirect(reverse("your-collections"))
    else:
        messages.add_message(
            request,
            messages.INFO,
            "You're not allowed to delete this collection.In order to delete a collection you must be the owner.",
        )
        return HttpResponseRedirect(collection.get_absolute_url())


def serialize_collection_sounds(collection):
    """Return lightweight collection sound metadata shipped as client-side JSON."""
    collection_sounds = list(Sound.objects.bulk_sounds_for_collection(collection_id=collection.id))
    cs_dates = dict(CollectionSound.objects.filter(collection=collection).values_list("sound_id", "created"))
    featured_order = {sound_id: order for order, sound_id in enumerate(collection.featured_sound_ids)}
    return [
        {
            "id": sound.id,
            "name": sound.original_filename,
            "username": sound.username,
            "duration": sound.duration,
            "date_added": cs_dates.get(sound.id, sound.created),
            "featured_order": featured_order.get(sound.id),
        }
        for sound in collection_sounds
    ]


@login_required
@resolve_collection_from_url
def render_collection_cards(request, collection):
    """Render with-actions sound cards for a caller-specified id list.

    Scoped to a collection: the caller must be its owner or a maintainer.

    Used by the collection-edit grid, where the client is the source of truth
    for which sounds appear and in what order. Featured / removed button state
    is restored client-side from the editor's store, so this endpoint does not
    take a ``featured`` parameter.

    Query params:
      - ``ids`` (required): comma-separated integer ids. Order is preserved;
        unknown/non-public ids are silently dropped. Capped at
        ``settings.MAX_SOUNDS_PER_COLLECTION``.
      - ``page``, ``total`` (optional): when both are provided, an
        ``hx-swap-oob`` paginator block is emitted alongside the cards so htmx
        swaps both regions in a single response.
      - ``q`` (optional): the active search query, used only to render an
        empty-state message when the supplied id list is empty.
    """
    is_owner = request.user == collection.user
    is_maintainer = not is_owner and collection.maintainers.filter(id=request.user.id).exists()
    if not is_owner and not is_maintainer:
        return HttpResponse(status=403)
    raw_ids = request.GET.get("ids", "")
    ids = [int(x) for x in raw_ids.split(",") if x.isdigit()][: settings.MAX_SOUNDS_PER_COLLECTION]

    sounds_by_id = {s.id: s for s in Sound.objects.bulk_query_id_public(ids)} if ids else {}
    sounds = [sounds_by_id[i] for i in ids if i in sounds_by_id]

    tvars = {
        "sounds": sounds,
        "max_sounds": settings.MAX_SOUNDS_PER_COLLECTION,
        "current_search": request.GET.get("q", "").strip(),
    }

    raw_page = request.GET.get("page")
    raw_total = request.GET.get("total")
    if raw_page and raw_total:
        try:
            total_pages = int(raw_total)
            page_num = max(1, min(int(raw_page), max(1, total_pages)))
            paginator_ns = SimpleNamespace(num_pages=total_pages)
            page_dict = {
                "has_previous": page_num > 1,
                "has_next": page_num < total_pages,
                "previous_page_number": page_num - 1,
                "next_page_number": page_num + 1,
            }
            tvars.update(
                build_paginator_template_context(
                    paginator_ns, page_dict, page_num, base_path=request.path, base_query=request.GET
                )
            )
            tvars["has_paginator"] = True
        except (ValueError, TypeError):
            pass

    return render(request, "collections/_collection_edit_cards.html", tvars)


@login_required
@resolve_collection_from_url
def edit_collection(request, collection):
    maintainers_query = User.objects.filter(collection_maintainer=collection.id)
    collection_maintainers = ",".join(str(u) for u in maintainers_query.values_list("id", flat=True))
    is_owner = request.user == collection.user
    is_maintainer = not is_owner and maintainers_query.filter(id=request.user.id).exists()
    if not is_owner and not is_maintainer:
        return HttpResponseRedirect(collection.get_absolute_url())

    FormClass = CollectionEditForm if is_owner else CollectionEditFormAsMaintainer

    if request.method == "POST":
        form = FormClass(
            request.POST, instance=collection, label_suffix="", is_owner=is_owner, is_maintainer=is_maintainer
        )
        if form.is_valid():
            form.save(user_adding_sound=request.user)
            return HttpResponseRedirect(collection.get_absolute_url())
    else:
        featured_sounds_str = ",".join(str(sid) for sid in collection.featured_sound_ids)
        form = FormClass(
            instance=collection,
            initial=dict(maintainers=collection_maintainers, featured_sounds=featured_sounds_str),
            label_suffix="",
            is_owner=is_owner,
            is_maintainer=is_maintainer,
        )

    form.collection_maintainers_objects = maintainers_query

    sounds_data = serialize_collection_sounds(collection)

    tvars = {
        "form": form,
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "sort_options": settings.COLLECTION_SORT_OPTIONS,
        "sounds_data": sounds_data,
        "current_sort": request.GET.get("s") or settings.COLLECTION_SORT_DEFAULT,
        "current_search": request.GET.get("q", "").strip(),
        "render_cards_url": collection.get_url("collection-render-cards"),
        "page_config": {
            "sounds_per_page": settings.BOOKMARKS_PER_PAGE,
            "max_sounds": settings.MAX_SOUNDS_PER_COLLECTION,
            "max_featured": settings.MAX_FEATURED_SOUNDS_PER_COLLECTION,
        },
    }

    return render(request, "collections/edit_collection.html", tvars)


@login_required
@resolve_collection_from_url
def download_collection(request, collection):
    collection_sounds = CollectionSound.objects.filter(collection=collection).values("sound_id")
    sounds_list = Sound.objects.filter(
        id__in=collection_sounds, processing_state="OK", moderation_state="OK"
    ).select_related("user", "license")

    if "range" not in request.headers:
        """
        Download managers and some browsers use the range header to download files in multiple parts. We have observed 
        that all clients first make a GET with no range header (to get the file length) and then make multiple other 
        requests. We ignore all requests that have range header because we assume that a first query has already been 
        made. Unlike in pack downloads, here we do not guard against multiple consecutive downloads.
        """
        cd = CollectionDownload.objects.create(user=request.user, collection=collection)
        cds = []
        for sound in sounds_list:
            cds.append(CollectionDownloadSound(sound=sound, collection_download=cd, license=sound.license))
        CollectionDownloadSound.objects.bulk_create(cds)

    licenses_url = collection.licenses_url
    licenses_content = collection.get_attribution(sound_qs=sounds_list)
    return download_sounds(licenses_url, licenses_content, sounds_list, collection.download_filename)


@resolve_collection_from_url
def collection_downloaders(request, collection):
    if not request.GET.get("ajax"):
        # If not loaded as a modal, redirect to collection page with parameter to open modal
        return HttpResponseRedirect(collection.get_absolute_url() + "?downloaders=1")

    qs = CollectionDownload.objects.filter(collection=collection)

    num_items_per_page = settings.USERS_PER_DOWNLOADS_MODAL_PAGE
    pagination = paginate(request, qs, num_items_per_page, object_count=collection.num_downloads)
    page = pagination["page"]

    # Get all users+profiles for the user ids
    userids = [d.user_id for d in list(page)]
    users = User.objects.filter(pk__in=userids).select_related("profile")
    user_map = {}
    for u in users:
        user_map[u.id] = u

    download_list = []
    for d in page:
        download_list.append({"created": d.created, "user": user_map[d.user_id]})
    download_list = sorted(download_list, key=itemgetter("created"), reverse=True)

    tvars = {"collection": collection, "download_list": download_list}
    tvars.update(pagination)
    return render(request, "sounds/modal_downloaders.html", tvars)


@resolve_collection_from_url
def collection_licenses(request, collection):
    attribution = collection.get_attribution()
    return HttpResponse(attribution, content_type="text/plain")


@resolve_collection_from_url
def add_sounds_modal_for_collection_edit(request, collection):
    tvars = add_sounds_modal_helper(request)
    tvars.update({"modal_title": "Add sounds to collection", "help_text": "Modal to add sounds to your collection"})
    return render(request, "sounds/modal_add_sounds.html", tvars)


@resolve_collection_from_url
def add_maintainer_modal(request, collection):
    form = MaintainerForm()
    # TODO: the below statements exclude users with whitespaces in their usernames (and they still exist)
    usernames = request.GET.get("q", "").split(",")
    usernames = [u.strip() for u in usernames]
    new_maintainers = User.objects.filter(is_active=True, username__in=usernames)
    not_found_users = []
    not_found_message = False
    for usr in usernames:
        if usr != "" and usr not in list(new_maintainers.values_list("username", flat=True)):
            not_found_users.append(usr)

    if len(not_found_users) > 0:
        not_found_message = "The following users could not be found: "
        for usr in not_found_users:
            if usr == not_found_users[-1]:
                not_found_message += usr + "."
            else:
                not_found_message += usr + ", "

    tvars = {
        "collection": collection,
        "help_text": "Add maintainers to your collection",
        "form": form,
        "new_maintainers": new_maintainers,
        "not_found_msg": not_found_message,
    }

    return render(request, "collections/modal_add_maintainer.html", tvars)
