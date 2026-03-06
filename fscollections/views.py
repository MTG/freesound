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

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import CharField, Q
from django.db.models.functions import Cast
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

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
from utils.pagination import paginate


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
    is_owner = False
    is_maintainer = False
    maintainers = []

    is_maintainer = collection.maintainers.filter(username=user.username).exists()
    is_owner = user == collection.user
    maintainers = collection.maintainers.all()

    sort_by = request.GET.get("s", settings.COLLECTION_SORT_DEFAULT)
    search_query = request.GET.get("q", "").strip()
    collection_sounds = Sound.objects.bulk_sounds_for_collection(
        collection_id=collection.id, sort_by=sort_by, featured_sound_ids=collection.featured_sound_ids
    )

    # Filter sounds by search query if provided
    if search_query:
        collection_sounds = collection_sounds.filter(Q(original_filename__icontains=search_query)).distinct()

    paginator = paginate(request, collection_sounds, settings.BOOKMARKS_PER_PAGE)
    page_sounds = Sound.objects.ordered_ids([sound.id for sound in paginator["page"].object_list])

    tvars = {
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "maintainers": maintainers,
        "sort_by": sort_by,
        "sort_options": settings.COLLECTION_SORT_OPTIONS,
        "search_query": search_query,
    }
    tvars.update(paginator)
    tvars["page_collection_and_sound_objects"] = zip(paginator["page"].object_list, page_sounds)

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


@login_required
@resolve_collection_from_url
def edit_collection(request, collection):
    initial_sound_ids = ",".join(str(s) for s in Sound.objects.filter(collections=collection).values_list("id", flat=True))
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
            # NOTE: in this form's validation, errors are raised for each specific field, so when there is a submission attempt the error
            # is displayed within it. However, fields containing errors are removed from the clean data but we are still interested in
            # preserving its value. Therefore, we re-initialize a form according to the user's permissions preserving the field's validated data if so,
            # and in case of error, we take its value from the POST request. The error messages are then attached to the form so that they're displayed.
            errors_data = form.errors
            new_form_data = {
                field: form.cleaned_data.get(field, request.POST.get(field))
                for field in form.fields
            }
            form = FormClass(initial=new_form_data, label_suffix="", is_owner=is_owner, is_maintainer=is_maintainer)
            form._errors = errors_data
    else:
        featured_sounds_str = ",".join(str(sid) for sid in collection.featured_sound_ids)
        form = FormClass(
            instance=collection,
            initial=dict(maintainers=collection_maintainers, featured_sounds=featured_sounds_str),
            label_suffix="",
            is_owner=is_owner,
            is_maintainer=is_maintainer,
        )
    sort_by = request.GET.get("s", settings.COLLECTION_SORT_DEFAULT)
    search_query = request.GET.get("q", "").strip()

    # Merge client-side featured IDs with DB-persisted ones for sorting
    client_featured_str = request.GET.get("featured_sounds", "")
    client_featured_ids = [int(x) for x in client_featured_str.split(",") if x.strip().isdigit()]
    if client_featured_ids:
        merged_featured = list(collection.featured_sound_ids) + [
            fid for fid in client_featured_ids if fid not in collection.featured_sound_ids
        ]
    else:
        merged_featured = collection.featured_sound_ids

    current_sounds = Sound.objects.bulk_sounds_for_collection(
        collection_id=collection.id, sort_by=sort_by, featured_sound_ids=merged_featured
    )

    # Union in sounds added via the modal (not yet persisted)
    added_ids_str = request.GET.get("added_sounds", "")
    added_ids = [int(x) for x in added_ids_str.split(",") if x.strip().isdigit()]
    if added_ids:
        added_qs = Sound.objects.filter(id__in=added_ids, moderation_state="OK", processing_state="OK")
        current_sounds = (current_sounds | added_qs).distinct()

    # Filter sounds by search query if provided
    if search_query:
        current_sounds = current_sounds.annotate(
            created_str=Cast("created", output_field=CharField())
        ).filter(
            Q(original_filename__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(created_str__icontains=search_query)
        ).distinct()

    # Paginate the sounds
    paginator_data = paginate(request, current_sounds, settings.BOOKMARKS_PER_PAGE)
    page_sounds = Sound.objects.ordered_ids([sound.id for sound in paginator_data["page"].object_list])

    form.collection_sound_objects = page_sounds
    form.collection_maintainers_objects = maintainers_query
    form.featured_sound_ids = merged_featured

    total_sounds_count = paginator_data["paginator"].count

    tvars = {
        "form": form,
        "collection": collection,
        "is_owner": is_owner,
        "is_maintainer": is_maintainer,
        "initial_sound_ids": initial_sound_ids,
        "max_sounds_per_collection": settings.MAX_SOUNDS_PER_COLLECTION,
        "sort_by": sort_by,
        "sort_options": settings.COLLECTION_SORT_OPTIONS,
        "total_sounds_count": total_sounds_count,
        "search_query": search_query,
    }
    tvars.update(paginator_data)

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
