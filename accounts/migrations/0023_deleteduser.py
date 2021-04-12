# -*- coding: utf-8 -*-
# Generated by Django 1.11.20 on 2019-09-27 16:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_auto_20190611_1647'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeletedUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=150)),
                ('email', models.CharField(max_length=200)),
                ('deletion_date', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('type', models.CharField(choices=[(b'ss', b'Sound spammer'), (b'fs', b'Forum spammer'), (b'ad', b'Deleted by an admin'), (b'sd', b'Self deleted')], default=b'ss', max_length=2)),
            ],
        ),
    ]
