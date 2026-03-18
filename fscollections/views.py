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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import strip_tags

from freesound import settings
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

    previews_url = settings.CDN_PREVIEWS_URL if settings.USE_CDN_FOR_PREVIEWS else settings.PREVIEWS_URL
    displays_url = settings.CDN_DISPLAYS_URL if settings.USE_CDN_FOR_DISPLAYS else settings.DISPLAYS_URL

    tvars = {
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "maintainers": maintainers,
        "sort_options": settings.COLLECTION_SORT_OPTIONS,
        "sounds_data": serialize_collection_sounds(collection),
        "featured_sound_ids": list(collection.featured_sound_ids),
        "page_config": {
            "previews_url": previews_url,
            "displays_url": displays_url,
            "sounds_per_page": settings.BOOKMARKS_PER_PAGE,
        },
    }

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
    """Serialize all sounds in a collection as a list of dicts for client-side rendering."""
    collection_sounds = Sound.objects.bulk_sounds_for_collection(collection_id=collection.id)
    cs_dates = dict(CollectionSound.objects.filter(collection=collection).values_list("sound_id", "created"))
    return [
        {
            "id": sound.id,
            "name": sound.original_filename,
            "username": sound.username,
            "user_id": sound.user_id,
            "duration": sound.duration,
            "samplerate": sound.samplerate,
            "created": sound.created,
            "date_added": cs_dates.get(sound.id, sound.created),
            "description": strip_tags(sound.description or "")[:200],
            "num_downloads": sound.num_downloads or 0,
            "num_comments": sound.num_comments or 0,
            "num_ratings": sound.num_ratings or 0,
            "avg_rating": round(sound.avg_rating / 2, 1) if (sound.num_ratings or 0) >= settings.MIN_NUMBER_RATINGS else None,
            "license_icon": sound.license.icon_name if sound.license_id else None,
            "license_name": sound.license.name if sound.license_id else None,
            "pack_id": sound.pack_id,
            "pack_name": getattr(sound.pack, "name", None) if sound.pack_id else None,
            "has_geotag": hasattr(sound, "geotag") and sound.geotag is not None,
            "remix_group": bool(getattr(sound, "remixgroup_id", None)),
            "ready_for_similarity": sound.ready_for_similarity,
        }
        for sound in collection_sounds
    ]


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

    previews_url = settings.CDN_PREVIEWS_URL if settings.USE_CDN_FOR_PREVIEWS else settings.PREVIEWS_URL
    displays_url = settings.CDN_DISPLAYS_URL if settings.USE_CDN_FOR_DISPLAYS else settings.DISPLAYS_URL

    form.collection_maintainers_objects = maintainers_query

    tvars = {
        "form": form,
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "sort_options": settings.COLLECTION_SORT_OPTIONS,
        "sounds_data": serialize_collection_sounds(collection),
        "featured_sound_ids": list(collection.featured_sound_ids),
        "page_config": {
            "previews_url": previews_url,
            "displays_url": displays_url,
            "sounds_per_page": settings.BOOKMARKS_PER_PAGE,
            "max_sounds": settings.MAX_SOUNDS_PER_COLLECTION,
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
