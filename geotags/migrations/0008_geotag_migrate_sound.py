# This needs to be run in a separate transaction due to indexes

from django.db import migrations


def migrate_geotags(apps, schema_editor):
    GeoTag = apps.get_model('geotags', 'GeoTag')
    Sound = apps.get_model('sounds', 'Sound')
    to_update = []
    to_delete = []
    for geotag in GeoTag.objects.prefetch_related('sound_set').all():
        sounds = geotag.sound_set.all()
        if len(sounds) == 1:
            geotag.sound2_id = sounds.first().id
            to_update.append(geotag)
        else:
            to_delete.append(geotag)
    GeoTag.objects.bulk_update(to_update, ['sound2'])
    print(f"Deleting {len(to_delete)} geotags with 0 sounds")
    GeoTag.objects.filter(id__in=[gt.id for gt in to_delete]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('geotags', '0007_geotag_sound2'),
    ]

    operations = [
        migrations.RunPython(migrate_geotags),
    ]
