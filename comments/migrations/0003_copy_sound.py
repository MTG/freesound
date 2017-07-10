from django.db import migrations, transaction


def forwards_func(apps, schema_editor):
    """
    Migration from old model to the new one."
    """
    Comment = apps.get_model("comments", "Comment")
    Sound = apps.get_model("sounds", "Sound")
    with transaction.atomic():
        for comment in Comment.objects.all():
            s = Sound.objects.get(pk=comment.object_id)
            comment.sound = s
            comment.save()


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0002_comment_sound'),
    ]

    operations = [
        migrations.RunPython(
            forwards_func,
        ),
    ]
