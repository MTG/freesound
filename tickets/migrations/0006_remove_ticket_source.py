# Generated by Django 1.9.5 on 2016-07-13 10:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0005_auto_20160608_1546'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ticket',
            name='source',
        ),
    ]
