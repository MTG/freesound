# Generated by Django 1.11.20 on 2020-04-29 15:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sounds', '0035_auto_20190724_1509'),
    ]

    operations = [
        migrations.AddField(
            model_name='sound',
            name='uploaded_with_bulk_upload_progress',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='sounds.BulkUploadProgress'),
        ),
    ]
