# Generated by Django 3.2.23 on 2025-01-30 20:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('geotags', '0005_alter_geotag_information'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='geotag',
            name='user',
        ),
    ]
