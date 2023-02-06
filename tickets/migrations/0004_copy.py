from tickets import TICKET_STATUS_CLOSED
from django.db import models, migrations
from django.contrib.contenttypes.models import ContentType

def forwards_func(apps, schema_editor):
    "Migration from old model to the new one."
    Ticket = apps.get_model("tickets", "Ticket")
    Sound = apps.get_model("sounds", "Sound")
    db_alias = schema_editor.connection.alias
    for t in Ticket.objects.using(db_alias).all():
        if t.content:
            sound_id = t.content.object_id
            try:
                s = Sound.objects.get(id=sound_id)
                t.sound = s
                t.save()
            except Sound.DoesNotExist:
                t.content = None
                t.status = TICKET_STATUS_CLOSED
                t.save()

def backwards_func(apps, schema_editor):
    "Migration from new model to the old one."
    Ticket = apps.get_model("tickets", "Ticket")
    LinkedContent = apps.get_model("tickets", "LinkedContent")
    Sound = apps.get_model("sounds", "Sound")
    ct = ContentType.objects.get(app_label="sounds", model="sound")
    db_alias = schema_editor.connection.alias
    for t in Ticket.objects.using(db_alias).all():
        if t.sound:
            l = LinkedContent.objects.create(
                    content_type_id = ct.id,
                    object_id = t.sound.id)
            t.content = l
            t.save()

class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_ticket_sound'),
    ]

    operations = [
        migrations.RunPython(
            forwards_func,
            reverse_code=backwards_func
        ),
    ]
