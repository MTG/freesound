# Generated by Django 1.11 on 2018-03-21 10:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sounds', '0021_auto_20180320_1554'),
    ]

    operations = [
        migrations.AlterField(
            model_name='download',
            name='sound',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='downloads', to='sounds.Sound'),
        ),
    ]
