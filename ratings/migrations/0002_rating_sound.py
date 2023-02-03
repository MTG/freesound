from django.db import migrations, models
from django.conf import settings
import django.db.models.deletion


def delete_ratings_with_no_sounds(apps, schema_editor):
    Sound = apps.get_model("sounds", "Sound")
    Rating = apps.get_model("ratings", "Rating")

    # It might be that a Ratings references a Sound that doesn't exists
    # First remove all ratings for non existing Sounds
    object_ids = Rating.objects.values_list("object_id", flat=True).distinct()
    sound_ids = Sound.objects.values_list("id", flat=True)

    missing_sound_ids = set(object_ids) - set(sound_ids)
    Rating.objects.filter(object_id__in=missing_sound_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ratings', '0001_initial'),
        ('sounds', '0012_auto_20171002_1710'),
    ]

    operations = [
        migrations.RunPython(
            delete_ratings_with_no_sounds, migrations.RunPython.noop
        ),
        migrations.AlterUniqueTogether(
           name='rating',
           unique_together=(),
        ),
        migrations.RenameField(
            model_name='rating',
            old_name='object_id',
            new_name='sound',
        ),
        migrations.AlterField(
            model_name='rating',
            name='sound',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ratings',
                                    to='sounds.Sound'),
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together=(('user', 'sound'),),
        ),
        migrations.RemoveField(
            model_name='rating',
            name='content_type',
        ),
        migrations.RenameModel(
            old_name='Rating',
            new_name='SoundRating',
        ),
    ]
