from django.db import models, migrations
from django.contrib.contenttypes.models import ContentType

def forwards_func(apps, schema_editor):
    "Migration from old model to the new one."
    Ticket = apps.get_model("tickets", "Ticket")
    db_alias = schema_editor.connection.alias
    for ticket in Ticket.objects.all():
        last = ticket.messages.order_by('-created').all()
        if last.count():
            ticket.last_commenter = last[0].sender
            ticket.comment_date = last[0].created
            ticket.save()


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0007_auto_20170626_1755'),
    ]

    operations = [
        migrations.RunPython(
            forwards_func,
        ),
    ]
