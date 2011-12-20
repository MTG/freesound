from django.core.management.base import BaseCommand
from sounds.models import Pack

class Command(BaseCommand):
    args = ''
    help = "Find packs that need refreshing and create them"
    def handle(self, *args, **options):
        for pack in Pack.objects.filter(is_dirty=True):
            pack.create_zip()
