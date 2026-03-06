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

import re

from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.forms import Textarea, TextInput

from fscollections.models import Collection, CollectionSound
from sounds.models import Sound


class SelectCollectionOrNewCollectionForm(forms.Form):
    """This form unfolds all the available collections for the user in a modal and allows to select one.
    So far it is only used to add one sound to a collection interacting from the sound player (as previously done
    in Bookmarks). Available collections are those where the user is either the owner or a maintainer, with a number
    of sounds lower than MAX_SOUNDS_PER_COLLECTION and still do not contain the selected sound. New collections can be
    created with a custom name, or with the default name for the personal collection's name (Bookmark), if the user has
    not created any collection yet.

    Args:
        forms (Form): django Form class.

    Raises:
        forms.ValidationError: sound does not exist.
        forms.ValidationError: collection.num_sounds exceeds settings.MAX_SOUNDS_PER_COLLECTION.
        forms.ValidationError: user is not owner nor maintainer so lacks permission to edit the collection.
        forms.ValidationError: sound already exists in collection.
        forms.ValidationError: collection does not exist.
        forms.ValidationError: new collection name already exists in user's collection.
        forms.ValidationError: new collection name is empty
        forms.ValidationError: invalid selected category value

    Returns:
        save: returns the selected collection object to be used
    """

    collection = forms.ChoiceField(label=None, choices=[], required=True)

    new_collection_name = forms.CharField(label=None, max_length=128, required=False)

    use_last_collection = forms.BooleanField(widget=forms.HiddenInput(), required=False, initial=False)

    mark_as_featured = forms.BooleanField(label=False, required=False, initial=False)
    user_collections = None
    user_available_collections = None
    user_full_collections = None

    BOOKMARK_COLLECTION_CHOICE_VALUE = "-1"
    NEW_COLLECTION_CHOICE_VALUE = "0"

    def __init__(self, *args, **kwargs):
        self.user_collections = kwargs.pop("user_collections", False)
        self.user_saving_sound = kwargs.pop("user_saving_sound", False)
        self.sound_id = kwargs.pop("sound_id", False)

        if self.user_collections:
            # NOTE: as a solution to avoid duplicate sounds in a collection, Collections already containing the sound are not selectable
            # this is also useful to discard adding sounds to collections that are full (max_num_sounds)
            self.user_available_collections = (
                Collection.objects.filter(id__in=self.user_collections)
                .exclude(sounds__id=self.sound_id)
                .exclude(is_default_collection=True)
                .exclude(num_sounds__gte=settings.MAX_SOUNDS_PER_COLLECTION)
            )

        display_bookmark_collection = True
        try:
            # if the user already has a Bookmarks Collection, the default BOOKMARK COLLECTION CHOICE VALUE must be the ID of this collection
            default_collection = Collection.objects.get(user=self.user_saving_sound, is_default_collection=True)
            self.BOOKMARK_COLLECTION_CHOICE_VALUE = default_collection.id
            if CollectionSound.objects.filter(sound=self.sound_id, collection=default_collection).exists():
                # if the Bookmarks Collection already contains the sound, don't display it as an option
                display_bookmark_collection = False
        except Collection.DoesNotExist:
            pass

        super().__init__(*args, **kwargs)
        self.fields["collection"].choices = (
            ([(self.BOOKMARK_COLLECTION_CHOICE_VALUE, "My bookmarks")] if display_bookmark_collection else [])
            + [(self.NEW_COLLECTION_CHOICE_VALUE, "Create a new collection...")]
            + (
                [(collection.id, collection.name) for collection in self.user_available_collections]
                if self.user_available_collections
                else []
            )
        )

        self.fields["new_collection_name"].widget.attrs["placeholder"] = "Write a description for the new collection"
        self.fields["collection"].widget.attrs = {
            "data-grey-items": f"{self.BOOKMARK_COLLECTION_CHOICE_VALUE},{self.NEW_COLLECTION_CHOICE_VALUE}"
        }

    def save(self, *args, **kwargs):
        collection_to_use = None
        sound = Sound.objects.get(id=self.sound_id)

        if not self.cleaned_data["use_last_collection"]:
            if self.cleaned_data["collection"] == self.BOOKMARK_COLLECTION_CHOICE_VALUE:
                collection_to_use, _ = Collection.objects.get_or_create(
                    name="My bookmarks", user=self.user_saving_sound, is_default_collection=True
                )
                # TODO: what happens if user has more than one is_default_collection? Shouldn't happen but this needs a RESTRICTION
            elif self.cleaned_data["collection"] == self.NEW_COLLECTION_CHOICE_VALUE:
                if self.cleaned_data["new_collection_name"] != "":
                    collection = Collection.objects.create(
                        user=self.user_saving_sound, name=self.cleaned_data["new_collection_name"]
                    )
                    collection_to_use = collection
            else:
                collection_to_use = Collection.objects.get(id=self.cleaned_data["collection"])
        else:
            try:
                last_user_collection = Collection.objects.filter(user=self.user_saving_sound).order_by("-created")[0]
                collection_to_use = last_user_collection
            except IndexError:
                pass

        maintainers_list = list(collection_to_use.maintainers.all().values_list("id", flat=True))
        if self.user_saving_sound == collection_to_use.user:
            collection, _ = Collection.objects.get_or_create(name=collection_to_use.name, id=collection_to_use.id)
        elif self.user_saving_sound.id in maintainers_list:
            collection, _ = Collection.objects.get_or_create(name=collection_to_use.name, id=collection_to_use.id)
        CollectionSound.objects.get_or_create(
            user=self.user_saving_sound, collection=collection, sound=sound, defaults={"status": "OK"}
        )

        # Handle mark as featured
        if self.cleaned_data.get("mark_as_featured"):
            if sound.id not in collection.featured_sound_ids:
                collection.featured_sound_ids = collection.featured_sound_ids + [sound.id]
                collection.save(update_fields=["featured_sound_ids"])

        return collection

    def clean(self):
        clean_data = super().clean()
        try:
            sound = Sound.objects.get(id=self.sound_id, moderation_state="OK")
        except Sound.DoesNotExist:
            raise forms.ValidationError("Unexpected errors occured while handling the sound.")
        # existing collection selected
        try:
            if clean_data["collection"] != "0" and clean_data["new_collection_name"] == "":
                if clean_data["collection"] == "-1":
                    pass
                else:
                    try:
                        collection = Collection.objects.get(id=clean_data["collection"])

                        if collection.num_sounds >= settings.MAX_SOUNDS_PER_COLLECTION:
                            raise forms.ValidationError(
                                f"The chosen collection has reached the maximum number of sounds allowed ({settings.MAX_SOUNDS_PER_COLLECTION})"
                            )

                        maintainers_list = list(collection.maintainers.all().values_list("id", flat=True))
                        if (
                            self.user_saving_sound.id not in maintainers_list
                            and self.user_saving_sound != collection.user
                        ):
                            raise forms.ValidationError("You do not have permission to edit this collection.")

                        collection_sounds = Sound.objects.filter(collections=collection)
                        if sound in collection_sounds:
                            raise forms.ValidationError("This sound already exists in this collection")

                    except Collection.DoesNotExist:
                        raise forms.ValidationError("This collection does not exist.")
            elif clean_data["new_collection_name"] != "":
                if Collection.objects.filter(
                    user=self.user_saving_sound, name=clean_data["new_collection_name"]
                ).exists():
                    raise forms.ValidationError("You already have a collection with this name.")
            else:
                raise forms.ValidationError("Please introduce a valid name for the collection.")

        except KeyError:
            raise forms.ValidationError("The chosen collection is not valid.")
        return clean_data


class CollectionEditForm(forms.ModelForm):
    added_sounds = forms.CharField(
        widget=forms.widgets.HiddenInput(attrs={"id": "added_sound_ids"}),
        required=False,
    )

    removed_sounds = forms.CharField(
        widget=forms.widgets.HiddenInput(attrs={"id": "removed_sound_ids"}),
        required=False,
    )

    maintainers = forms.CharField(
        min_length=1, widget=forms.widgets.HiddenInput(attrs={"id": "maintainers"}), required=False
    )

    featured_sounds = forms.CharField(
        widget=forms.widgets.HiddenInput(attrs={"id": "featured_sounds", "name": "featured_sounds"}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.is_owner = kwargs.pop("is_owner", False)
        self.is_maintainer = kwargs.pop("is_maintainer", False)
        super().__init__(*args, **kwargs)
        self.fields["public"].label = "Visibility"

        self.fields["added_sounds"].help_text = (
            f"You have reached the maximum number of sounds available for a collection ({settings.MAX_SOUNDS_PER_COLLECTION}). "
            "In order to add new sounds, first remove some of the current ones."
        )

        if self.instance.is_default_collection:
            self.fields["name"].disabled = True
            self.fields["public"].disabled = True
            self.fields["description"].disabled = True

        if not self.is_owner and not self.is_maintainer:
            for field in self.fields:
                self.fields[field].disabled = True

    @staticmethod
    def _parse_id_set(value):
        return {int(i) for i in value.replace(" ", "").split(",") if i.isdigit()} if value else set()

    def clean_added_sounds(self):
        return self._parse_id_set(self.cleaned_data.get("added_sounds", ""))

    def clean_removed_sounds(self):
        return self._parse_id_set(self.cleaned_data.get("removed_sounds", ""))

    def clean_maintainers(self):
        return self._parse_id_set(self.cleaned_data.get("maintainers", ""))

    def clean_featured_sounds(self):
        return list(self._parse_id_set(self.cleaned_data.get("featured_sounds", "")))

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_owner and not self.is_maintainer:
            self.add_error(
                field=None, error=forms.ValidationError("You don't have permissions to edit this collection")
            )
        else:
            if cleaned_data["name"] != self.instance.name:
                if Collection.objects.filter(user=self.instance.user, name=cleaned_data["name"]).exists():
                    self.add_error("name", forms.ValidationError("You already have a collection with this name"))
                elif cleaned_data["name"].lower() == "my bookmarks":
                    self.add_error(
                        "name",
                        forms.ValidationError(
                            "This collection name is reserved for your personal default collection. Please choose another one."
                        ),
                    )
        added = cleaned_data.get("added_sounds", set())
        removed = cleaned_data.get("removed_sounds", set())
        # A sound that was added and then removed in the same session cancels out
        cancelled = added & removed
        cleaned_data["added_sounds"] = added = added - cancelled
        cleaned_data["removed_sounds"] = removed = removed - cancelled
        net_count = self.instance.num_sounds + len(added) - len(removed)
        if net_count > settings.MAX_SOUNDS_PER_COLLECTION:
            self.add_error(
                "added_sounds",
                forms.ValidationError(
                    f"You have exceeded the maximum number of sounds for a collection ({settings.MAX_SOUNDS_PER_COLLECTION})."
                ),
            )
        return cleaned_data

    def save(self, user_adding_sound):
        """Apply the pending delta (added/removed sounds and featured list) to the DB.

        Args:
            user_adding_sound (User): the user modifying the collection

        Returns:
            collection (Collection): the saved collection
        """
        collection = super().save(commit=False)
        sounds_to_add = self.cleaned_data["added_sounds"]
        sounds_to_remove = self.cleaned_data["removed_sounds"]

        if sounds_to_add:
            CollectionSound.objects.bulk_create(
                [CollectionSound(user=user_adding_sound, sound_id=snd, collection=collection, status="OK")
                 for snd in sounds_to_add],
                ignore_conflicts=True,
            )

        if sounds_to_remove:
            CollectionSound.objects.filter(collection=collection, sound_id__in=sounds_to_remove).delete()

        new_maintainers = self.cleaned_data["maintainers"]
        new_maintainers.discard(collection.user.id)
        collection.maintainers.set(new_maintainers)

        # Filter featured IDs to only sounds currently in the collection
        featured_ids = self.cleaned_data["featured_sounds"]
        final_sound_ids = set(Sound.objects.filter(collections=collection).values_list("id", flat=True))
        collection.featured_sound_ids = [sid for sid in featured_ids if sid in final_sound_ids]

        collection.save()
        return collection

    class Meta:
        model = Collection
        fields = ["name", "description", "public"]
        widgets = {
            "name": TextInput(),
            "description": Textarea(attrs={"rows": 5, "cols": 50}),
            "public": forms.RadioSelect(choices=[(True, "Public"), (False, "Private")], attrs={"class": "bw-radio"}),
        }


class CollectionEditFormAsMaintainer(CollectionEditForm):
    class Meta(CollectionEditForm.Meta):
        fields = CollectionEditForm.Meta.fields + ["added_sounds", "removed_sounds"] + ["maintainers"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if field not in ("added_sounds", "removed_sounds"):
                self.fields[field].disabled = True

    def clean(self):
        cleaned_data = super().clean()
        # NOTE: to prevent a maintainer from modifying any field from the server-side, the following validation is carried
        # All fields retrieved from the original model Collection (name, description, visibility) are compared to the original instance ones
        # and if any change in these is found, an error is raised. To prevent changes in "maintainers" even though it is included
        # in the form but disabled (to allow the user to view but not to modify the field), the original collection maintainers
        # are retrieved from DB to ensure no changes are applied to this attribute.
        cleaned_data["maintainers"] = set(self.instance.maintainers.values_list("id", flat=True))
        # Preserve featured_sounds from the original instance (maintainers cannot edit)
        cleaned_data["featured_sounds"] = list(self.instance.featured_sound_ids)
        for field in CollectionEditForm.Meta.fields:
            if cleaned_data[field] != getattr(self.instance, field):
                self.add_error(field, forms.ValidationError("You don't have permissions to edit this field"))
        return cleaned_data


class CreateCollectionForm(forms.ModelForm):
    user = None

    class Meta:
        model = Collection
        fields = ("name", "description")
        widgets = {
            "name": TextInput(),
            "description": Textarea(attrs={"rows": 5, "cols": 50}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["name"].label = False
        self.fields["name"].widget.attrs["placeholder"] = "Fill in the name for the new collection"
        self.fields["name"].widget.attrs["autocomplete"] = "off"
        self.fields["description"].label = False
        self.fields["description"].widget.attrs["placeholder"] = "Write a description for the new collection"

    def clean(self):
        if Collection.objects.filter(user=self.user, name=self.cleaned_data["name"]).exists():
            raise forms.ValidationError("You already have a collection with this name")
        return super().clean()


class MaintainerForm(forms.Form):
    maintainer = forms.CharField(
        widget=TextInput(
            attrs={
                "placeholder": "Please type the exact usernames separated by commas, then press Enter to search",
                "autocomplete": "off",
            }
        ),
        label=None,
        max_length=128,
        required=False,
    )

    collection = None

    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop("collection", False)
        super().__init__(*args, **kwargs)

    def clean(self):
        new_maintainers = self.cleaned_data["maintainer"].split(",").replace(" ", "")
        for username in new_maintainers:
            try:
                new_maintainer = User.objects.get(username=username)
                if new_maintainer in self.collection.maintainers.all():
                    raise forms.ValidationError("The user is already a maintainer")
                return super().clean()
            except User.DoesNotExist:
                raise forms.ValidationError("The user does not exist")
