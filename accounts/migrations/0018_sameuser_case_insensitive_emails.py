# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations
from django.db.models import Count
from django.db.models.functions import Lower
from utils.mail import transform_unique_email


def populate_sameuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    SameUser = apps.get_model('accounts', 'SameUser')

    # Get all case-insensitive duplicate email addresses which are used in more than one account
    email_addresses = User.objects.values_list(Lower('email'), flat=True)\
        .annotate(num_email=Count('email'))\
        .filter(num_email__gt=1)

    for email in email_addresses:
        # Get all users with that email address
        uss = User.objects.filter(email__iexact=email).order_by('-last_login').all()

        u1 = uss[0]
        for u2 in uss[1:]:
            # Assign users to variables and modify email of second user (to prevent the duplicates)
            u2.email = transform_unique_email(email)
            u2.save()

            # Create SameUser object
            SameUser.objects.create(main_user=u1, main_orig_email=email,
                                    secondary_user=u2, secondary_orig_email=email)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0017_auto_20180124_1150'),
    ]

    operations = [
        migrations.RunPython(populate_sameuser, migrations.RunPython.noop),
        migrations.RunSQL('CREATE UNIQUE INDEX "auth_user_email_upper_uniq" on "auth_user" (UPPER(email));')
    ]
