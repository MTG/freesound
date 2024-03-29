# Generated by Django 3.2.23 on 2024-01-02 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sounds', '0051_auto_20230929_1428'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sound',
            name='type',
            field=models.CharField(choices=[('wav', 'Wave'), ('ogg', 'Ogg Vorbis'), ('aiff', 'AIFF'), ('mp3', 'Mp3'), ('flac', 'Flac'), ('m4a', 'M4a'), ('wv', 'WavPack')], db_index=True, max_length=4),
        ),
    ]
