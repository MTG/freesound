# This needs to be run in a separate transaction due to indexes

from django.db import migrations


def migrate_geotags(apps, schema_editor):
    GeoTag = apps.get_model('geotags', 'GeoTag')
    Sound = apps.get_model('sounds', 'Sound')
    all_geotags = GeoTag.objects.prefetch_related('sound_set').all()
    print(f"Migrating {len(all_geotags)} geotags")
    batch_size = 1000
    for i in range(0, len(all_geotags), batch_size):
        batch = all_geotags[i:i+batch_size]
        to_update = []
        to_delete = []
        for geotag in batch:
            sounds = geotag.sound_set.all()
            if len(sounds) == 1:
                geotag.sound2_id = sounds.first().id
                to_update.append(geotag)
            else:
                to_delete.append(geotag)
        print(f"Updating {len(to_update)} geotags")
        GeoTag.objects.bulk_update(to_update, ['sound2'])
        if len(to_delete) > 0:
            print(f"Deleting {len(to_delete)} geotags with 0 sounds")
            GeoTag.objects.filter(id__in=[gt.id for gt in to_delete]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('geotags', '0007_geotag_sound2'),
    ]

    operations = [
        migrations.RunPython(migrate_geotags),
    ]
