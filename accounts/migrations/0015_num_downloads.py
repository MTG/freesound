# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def forwards_func(apps, schema_editor):
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Download = apps.get_model("sounds", "Download")
    Profile = apps.get_model("accounts", "Profile")
    db_alias = schema_editor.connection.alias
    for profile in Profile.objects.all():
        profile.num_sound_downloads = Download.objects.filter(user_id=profile.user_id, pack_id__isnull=True).count()
        profile.num_pack_downloads = Download.objects.filter(user_id=profile.user_id, sound_id__isnull=True).count()
        pack.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_auto_20171127_1552'),
    ]

    operations = [
        migrations.RunPython(forwards_func),
    ]
