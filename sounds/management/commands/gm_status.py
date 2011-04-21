from django.core.management.base import NoArgsCommand
from sounds.models import Sound
from django.conf import settings
import gearman

class Command(NoArgsCommand):
    help = 'Display gearman status'

    def handle(self, **options):
        gm_client = gearman.GearmanAdminClient(settings.GEARMAN_JOB_SERVERS)
        
        for task in gm_client.get_status():
            for key, value in task.items():
                self.stdout.write('%s: %s\n' % (key, str(value)))