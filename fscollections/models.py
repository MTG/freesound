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

from urllib.parse import quote

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Case, F, IntegerField, Sum, Value, When
from django.db.models.functions import Greatest
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.text import slugify

from freesound import settings
from sounds.models import License, Sound


class Collection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    created = models.DateTimeField(db_index=True, auto_now_add=True)
    modified = models.DateTimeField(db_index=True, auto_now=True)
    # TODO: description should be required (check how to display it in edit form + collectionsound form)
    description = models.TextField(blank=True)
    maintainers = models.ManyToManyField(User, related_name="collection_maintainer")
    sounds = models.ManyToManyField(Sound, through="CollectionSound", related_name="collections", blank=True)
    num_sounds = models.PositiveIntegerField(default=0)
    num_downloads = models.PositiveIntegerField(default=0)
    public = models.BooleanField(default=False)
    is_default_collection = models.BooleanField(default=False)
    featured_sound_ids = ArrayField(models.IntegerField(), size=settings.MAX_FEATURED_SOUNDS_PER_COLLECTION, blank=True, default=list)

    def __str__(self):
        return f"{self.name}"

    def collection_filter_value(self):
        return f'"{self.id}_{quote(self.name)}"'

    def get_collection_sounds_in_search_url(self):
        return f"{reverse('sounds-search')}?f=collection:{self.collection_filter_value()}"

    def get_attribution(self, sound_qs=None):
        # If no queryset of sounds is provided, take it from the collection
        if sound_qs is None:
            sound_qs = self.sounds.filter(processing_state="OK", moderation_state="OK").select_related(
                "user", "license"
            )

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
        result = self.sounds.aggregate(total_duration=Sum("duration"))
        return result["total_duration"] or 0

    def save(self, *args, **kwargs):
        # Update num_sounds count
        if self.pk:
            self.num_sounds = CollectionSound.objects.filter(collection=self).count()
        
        super().save(*args, **kwargs)

    def get_sounds(
        self,
        sort_by=None,
        limit=None,
        include_audio_descriptors=False,
        include_similarity_vectors=False,
        include_remix_subqueries=False,
    ):
        """Get sounds for this collection with sorting.
        
        Args:
            sort_by: Sort option key from settings.COLLECTION_SORT_OPTIONS.
                    Defaults to settings.COLLECTION_SORT_DEFAULT.
            limit: Optional limit on number of sounds returned
            include_audio_descriptors: Include audio descriptor data
            include_similarity_vectors: Include similarity vector data
            include_remix_subqueries: Include remix relationship data
        
        Returns:
            Sorted QuerySet of Sound objects
        """
        # Validate sort option, defaulting to COLLECTION_SORT_DEFAULT if invalid or None
        if sort_by not in settings.COLLECTION_SORT_OPTIONS:
            sort_by = settings.COLLECTION_SORT_DEFAULT

        qs = Sound.objects.bulk_sounds_for_collection(
            collection_id=self.id,
            include_audio_descriptors=include_audio_descriptors,
            include_similarity_vectors=include_similarity_vectors,
            include_remix_subqueries=include_remix_subqueries,
        )

        # Get the sort field from settings (value is the sort field directly)
        sort_field = settings.COLLECTION_SORT_OPTIONS[sort_by]

        # Apply sorting based on sort_by option (featured is when sort_by matches the default)
        if sort_field == "featured_order":
            # Featured sorting - direct access to self.featured_sound_ids
            if self.featured_sound_ids:
                ordering = Case(
                    *[When(id=sound_id, then=Value(i)) for i, sound_id in enumerate(self.featured_sound_ids)],
                    default=Value(len(self.featured_sound_ids)),
                    output_field=IntegerField()
                )
                qs = qs.annotate(featured_order=ordering).order_by(sort_field)
            # If no featured sounds, keep default queryset order
        elif sort_field:
            # Use the sort field from settings for other sort options
            qs = qs.order_by(sort_field)

        if limit:
            qs = qs[:limit]
        return qs


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


@receiver(post_save, sender=CollectionSound)
def update_collection_num_sounds(sender, instance, **kwargs):
    if instance:
        Collection.objects.filter(collectionsound=instance).update(num_sounds=Greatest(F("num_sounds") + 1, 0))


@receiver(m2m_changed, sender=CollectionSound)
def update_collection_num_sounds_bulk_changes(sender, instance, **kwargs):
    if instance:
        Collection.objects.filter(collectionsound=instance).update(num_sounds=Greatest(F("num_sounds") - 1, 0))


@receiver([post_save, post_delete], sender=CollectionSound)
def remove_not_valid_featured_sounds(sender, instance, **kwargs):
    """Remove featured_sound_ids that are no longer part of the collection."""
    if instance and instance.collection_id:
        collection = instance.collection
        if collection.featured_sound_ids:
            # Get current sound IDs in the collection
            valid_sound_ids = set(
                CollectionSound.objects.filter(collection=collection).values_list('sound_id', flat=True)
            )
            # Filter out any featured_sound_ids that are not in the collection
            valid_featured_ids = [sid for sid in collection.featured_sound_ids if sid in valid_sound_ids]
            if valid_featured_ids != collection.featured_sound_ids:
                Collection.objects.filter(id=collection.id).update(featured_sound_ids=valid_featured_ids)


@receiver([post_save, post_delete], sender=CollectionSound)
def mark_sound_dirty_on_collection_change(sender, instance, **kwargs):
    if instance:
        print(f"----------coll change: marking {instance.sound} dirty!!!!!!!!!!!!")
        Sound.objects.filter(id=instance.sound_id).update(is_index_dirty=True)


@receiver(pre_save, sender=Collection)
def mark_sounds_dirty_on_public_change(sender, instance, **kwargs):
    if instance and instance.pk:
        old_instance = Collection.objects.get(pk=instance.pk)
        if old_instance.public != instance.public:
            print("----------public changed !!!!!!!!!!!!")
            # Update all sounds in this collection
            instance.sounds.update(is_index_dirty=True)


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
