# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2023-02-06 18:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('comments', '0005_auto_20170710_1642'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='parent',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='comments.Comment'),
        ),
    ]
