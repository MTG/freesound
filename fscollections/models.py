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

from __future__ import annotations

from urllib.parse import quote

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Avg, Count, F, Sum
from django.db.models.functions import Greatest
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify

from freesound import settings
from sounds.models import License, LicenseSummaryMixin, Sound
from tags.models import Tag


class Collection(LicenseSummaryMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = models.DateTimeField(db_index=True, auto_now=True)
    # TODO: description should be required (check how to display it in edit form + collectionsound form)
    description = models.TextField(blank=True)
    maintainers = models.ManyToManyField(User, related_name="collection_maintainer")
    sounds: models.ManyToManyField[Sound, "CollectionSound"] = models.ManyToManyField(
        Sound, through="CollectionSound", related_name="collections", blank=True
    )
    num_sounds = models.PositiveIntegerField(default=0)
    num_downloads = models.PositiveIntegerField(default=0)
    public = models.BooleanField(default=False)
    is_default_collection = models.BooleanField(default=False)
    featured_sound_ids = ArrayField(
        models.IntegerField(), size=settings.MAX_FEATURED_SOUNDS_PER_COLLECTION, blank=True, default=list
    )

    def __str__(self):
        return f"{self.name}"

    def collection_filter_value(self):
        return f'"{self.id}_{quote(self.name)}"'

    def get_collection_sounds_in_search_url(self):
        return f"{reverse('sounds-search')}?f=collection:{self.collection_filter_value()}"

    @property
    def url_kwargs(self):
        return {"collection_id": self.id, "collection_name": slugify(self.name)}

    def get_url(self, url_name="collection"):
        return reverse(url_name, kwargs=self.url_kwargs)

    def get_absolute_url(self):
        return self.get_url()

    @property
    def edit_url(self):
        return self.get_url("edit-collection")

    @property
    def delete_url(self):
        return self.get_url("delete-collection")

    @property
    def download_url(self):
        return self.get_url("download-collection")

    @property
    def licenses_url(self):
        return self.get_url("collection-licenses")

    @property
    def add_sounds_modal_url(self):
        return self.get_url("add-sounds-modal-collection")

    @property
    def add_maintainers_modal_url(self):
        return self.get_url("add-maintainers-modal")

    def user_is_owner_or_maintainer(self, user):
        if not user or not user.is_authenticated:
            return False
        return user == self.user or self.maintainers.filter(id=user.id).exists()

    def update_num_sounds(self):
        # Single source of truth for the num_sounds recount
        self.num_sounds = Sound.objects.sounds_for_collection(self.id).count()
        Collection.objects.filter(id=self.id).update(num_sounds=self.num_sounds)

    def add_sound(self, sound, user, feature=False):
        """Add `sound` to this collection (idempotent), optionally featuring it.

        Returns True when featuring was requested but skipped because the collection already
        holds settings.MAX_FEATURED_SOUNDS_PER_COLLECTION featured sounds (the sound is still
        added in that case); returns False otherwise.
        """
        CollectionSound.objects.get_or_create(user=user, collection=self, sound=sound, defaults={"status": "OK"})
        if not feature or sound.id in self.featured_sound_ids:
            return False
        if len(self.featured_sound_ids) >= settings.MAX_FEATURED_SOUNDS_PER_COLLECTION:
            return True
        self.featured_sound_ids = self.featured_sound_ids + [sound.id]
        self.save(update_fields=["featured_sound_ids"])
        return False

    def get_attribution(self, sound_qs=None):
        # If no queryset of sounds is provided, take it from the collection
        if sound_qs is None:
            sound_qs = Sound.objects.bulk_sounds_for_collection(self.id)

        users = User.objects.filter(sounds__in=sound_qs).distinct()
        # Generate text file with license info
        licenses = License.objects.filter(sound__id__in=sound_qs).distinct()
        attribution = render_to_string(
            ("sounds/multiple_sounds_attribution.txt"),
            dict(type="Collection", users=users, object=self, licenses=licenses, sound_list=sound_qs),
        )
        return attribution

    @property
    def download_filename(self):
        name_slug = slugify(self.name)
        username_slug = slugify(self.user.username)
        return "%d__%s__%s.zip" % (self.id, username_slug, name_slug)

    def get_total_collection_sounds_length(self):
        result = Sound.objects.sounds_for_collection(self.id).aggregate(total_duration=Sum("duration"))
        return result["total_duration"] or 0

    @cached_property
    def ratings_data(self):
        # (avg rating, num sounds) of the collection sounds with at least MIN_NUMBER_RATINGS ratings
        result = (
            Sound.objects.sounds_for_collection(self.id)
            .filter(num_ratings__gte=settings.MIN_NUMBER_RATINGS)
            .aggregate(avg=Avg("avg_rating"), count=Count("id"))
        )
        return result["avg"] or 0, result["count"]

    @property
    def avg_rating(self):
        return self.ratings_data[0]

    @property
    def num_ratings(self):
        return self.ratings_data[1]

    @cached_property
    def licenses_data(self):
        licenses_data = list(Sound.objects.sounds_for_collection(self.id).values_list("license__name", "license_id"))
        license_ids = [lid for _, lid in licenses_data]
        license_names = [lname for lname, _ in licenses_data]
        return license_ids, license_names

    def get_collection_tags_bw(self):
        tags = (
            Tag.objects.filter(soundtag__sound__in=Sound.objects.sounds_for_collection(self.id))
            .annotate(count=Count("soundtag"))
            .order_by("-count")[:10]
        )
        return [{"name": tag.name, "count": tag.count, "browse_url": reverse("tags", args=[tag.name])} for tag in tags]

    def save(self, *args, **kwargs):
        # Update num_sounds count
        if self.pk:
            self.num_sounds = Sound.objects.sounds_for_collection(self.id).count()

        super().save(*args, **kwargs)


class CollectionSound(models.Model):
    # this model relates collections and sounds
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, related_name="collectionsound", on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    STATUS_CHOICES = (
        ("PE", "Pending"),
        ("OK", "Accepted"),
        ("RE", "Refused"),
    )
    status = models.CharField(db_index=True, max_length=2, choices=STATUS_CHOICES, default="PE")
    # sound won't be added to collection until maintainers approve the sound

    class Meta:
        unique_together = ("sound", "collection")


@receiver([post_save, post_delete], sender=CollectionSound)
def update_collection_num_sounds(sender, instance, **kwargs):
    if instance and instance.collection_id:
        instance.collection.update_num_sounds()


@receiver(post_delete, sender=CollectionSound)
def remove_not_valid_featured_sounds(sender, instance, **kwargs):
    """Remove featured_sound_ids that are no longer part of the collection."""
    if instance and instance.collection_id:
        collection = instance.collection
        if collection.featured_sound_ids:
            # Get current accepted sound IDs in the collection
            valid_sound_ids = set(
                CollectionSound.objects.filter(collection=collection, status="OK").values_list("sound_id", flat=True)
            )
            # Filter out any featured_sound_ids that are not in the collection
            valid_featured_ids = [sid for sid in collection.featured_sound_ids if sid in valid_sound_ids]
            if valid_featured_ids != collection.featured_sound_ids:
                Collection.objects.filter(id=collection.id).update(featured_sound_ids=valid_featured_ids)


@receiver(post_save, sender=CollectionSound)
def mark_sound_dirty_on_collection_add(sender, instance, **kwargs):
    if instance:
        Sound.objects.filter(id=instance.sound_id).update(is_index_dirty=True)


@receiver(post_delete, sender=CollectionSound)
def mark_sound_dirty_on_collection_remove(sender, instance, **kwargs):
    if instance:
        Sound.objects.filter(id=instance.sound_id).update(is_index_dirty=True)


class CollectionDownload(models.Model):
    user = models.ForeignKey(User, related_name="collection_downloads", on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, related_name="collection", on_delete=models.CASCADE)
    created = models.DateTimeField(db_index=True, auto_now_add=True)

    class Meta:
        ordering = ("-created",)


class CollectionDownloadSound(models.Model):
    sound = models.ForeignKey(Sound, on_delete=models.CASCADE)
    collection_download = models.ForeignKey(CollectionDownload, on_delete=models.CASCADE)
    license = models.ForeignKey(License, on_delete=models.CASCADE)


@receiver(post_save, sender=CollectionDownload)
def update_collection_downloads(sender, instance, **kwargs):
    if instance:
        Collection.objects.filter(id=instance.collection.id).update(num_downloads=Greatest(F("num_downloads") + 1, 0))


@receiver(post_delete, sender=CollectionDownload)
def update_collection_downloads_on_delete(sender, instance, **kwargs):
    if instance:
        Collection.objects.filter(id=instance.collection.id).update(num_downloads=Greatest(F("num_downloads") - 1, 0))
