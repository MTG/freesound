# Generated by Django 1.11 on 2017-07-10 15:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('donations', '0005_donationsemailsettings'),
    ]

    operations = [
        migrations.RenameField(
            model_name='donationsemailsettings',
            old_name='days_after_donation',
            new_name='minimum_days_since_last_donation',
        ),
        migrations.AddField(
            model_name='donationsemailsettings',
            name='minimum_days_since_last_donation_email',
            field=models.PositiveIntegerField(default=90, help_text="Don't send a donation email if the last one was sent in less than X days"),
        ),
    ]
