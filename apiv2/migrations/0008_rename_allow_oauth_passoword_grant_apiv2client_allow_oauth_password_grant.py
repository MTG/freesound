# Generated by Django 4.2.19 on 2025-03-19 11:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apiv2', '0007_auto_20230201_1102'),
    ]

    operations = [
        migrations.RenameField(
            model_name='apiv2client',
            old_name='allow_oauth_passoword_grant',
            new_name='allow_oauth_password_grant',
        ),
    ]
