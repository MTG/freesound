# Generated by Django 1.11.20 on 2019-05-28 15:54

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0008_copy_message_to_ticket'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ticket',
            options={'ordering': ('-created',), 'permissions': (('can_moderate', 'Can moderate stuff.'),)},
        ),
        migrations.AlterModelOptions(
            name='ticketcomment',
            options={'ordering': ('-created',)},
        ),
    ]
