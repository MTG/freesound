# Generated by Django 1.11.20 on 2019-10-10 15:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_auto_20191010_1448'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deleteduser',
            name='reason',
            field=models.CharField(choices=[(b'sp', b'Spammer'), (b'ad', b'Deleted by an admin'), (b'sd', b'Self deleted')], max_length=2),
        ),
    ]
