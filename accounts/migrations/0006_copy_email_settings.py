# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tickets import TICKET_STATUS_CLOSED
from django.db import models, migrations
from django.contrib.contenttypes.models import ContentType

def forwards_func(apps, schema_editor):
    """Migration from old model to the new one."""
    Profile = apps.get_model("accounts", "Profile")
    EmailPreferenceType= apps.get_model("accounts", "EmailPreferenceType")
    UserEmailSetting = apps.get_model("accounts", "UserEmailSetting")
    db_alias = schema_editor.connection.alias

    for p in Profile.objects.using(db_alias).filter(enabled_stream_emails=True):
        email = EmailPreferenceType.objects.get(name="stream_emails")
        UserEmailSetting.objects.create(email_type=email, user=p.user)


def backwards_func(apps, schema_editor):
    """Migration from new model to the old one."""
    UserEmailSetting = apps.get_model("accounts", "UserEmailSetting")
    db_alias = schema_editor.connection.alias
    for s in UserEmailSetting.objects.using(db_alias)\
            .filter(email_type__name="stream_email").all():
            profile = s.user.profile
            profile.enabled_stream_emails = True
            profile.save()

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_emailpreferencetype_useremailsetting'),
    ]

    operations = [
        migrations.RunPython(
            forwards_func,
            reverse_code=backwards_func
        ),
    ]
