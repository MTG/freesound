from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fscollections", "0004_alter_collection_featured_sound_ids"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="collection",
            constraint=models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_collection=True),
                name="unique_default_collection_per_user",
            ),
        ),
    ]
