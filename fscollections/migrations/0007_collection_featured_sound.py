# Generated by Django 3.2.23 on 2025-03-05 11:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sounds', '0052_alter_sound_type'),
        ('fscollections', '0006_auto_20250213_1108'),
    ]

    operations = [
        migrations.AddField(
            model_name='collection',
            name='featured_sound',
            field=models.ForeignKey(null=True, blank=True, default=None, on_delete=django.db.models.deletion.CASCADE, to='sounds.sound'),
        ),
    ]
