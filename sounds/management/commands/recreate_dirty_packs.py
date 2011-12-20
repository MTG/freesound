from django.core.management.base import BaseCommand
from sounds.models import Pack
import time
import logging

class Command(BaseCommand):
    args = ''
    help = "Find packs that need refreshing and create them"
    def handle(self, *args, **options):
        logger = logging.getLogger('web')
        t1 = time.time()
        for pack in Pack.objects.filter(is_dirty=True):
            pack.create_zip()
            
        t2 = time.time()
        logger.info('recreate_dirty_packs === Duration: %s' % (t2-t1))