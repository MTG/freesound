from django.db import migrations, transaction


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0002_comment_sound'),
    ]

    operations = [
        migrations.RunSQL("update comments_comment set sound_id = object_id",
            reverse_sql="update comments_comment set sound_id=null")
    ]
