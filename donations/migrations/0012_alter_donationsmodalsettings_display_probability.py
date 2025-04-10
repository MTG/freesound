# Generated by Django 4.2.19 on 2025-03-19 11:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('donations', '0011_auto_20230206_1820'),
    ]

    operations = [
        migrations.AlterField(
            model_name='donationsmodalsettings',
            name='display_probability',
            field=models.FloatField(default=0.25, help_text='probability of the modal being shown once all previous requirements are met'),
        ),
    ]
