# Generated by Django 1.11 on 2017-07-11 10:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_profile_last_donation_email_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='donations_reminder_email_sent',
            field=models.BooleanField(default=False),
        ),
    ]
