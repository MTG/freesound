# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db.models import F
from django.db import migrations, models

def forwards(apps, schema_editor):
    Sound = apps.get_model("sounds", "Sound")
    Rating = apps.get_model("ratings", "Rating")

    # It might be that a Ratings references a Sound that doesn't exists
    # First remove all ratings for non existing Sounds
    object_ids = Rating.objects.values_list("object_id", flat=True).distinct()
    sound_ids = Sound.objects.values_list("id", flat=True)

    map_sounds = {k: v for v, k in enumerate(list(sound_ids))}
    missing_sound_ids = [x for x in list(object_ids) if x not in map_sounds]
    Rating.objects.filter(object_id__in=missing_sound_ids).delete()

    # Then copy value of object_id to sound_id
    Rating.objects.update(sound_id=F('object_id'))


class Migration(migrations.Migration):

    dependencies = [
        ('ratings', '0002_rating_sound'),
    ]

    operations = [
        migrations.RunPython(
            forwards,
        ),
    ]
