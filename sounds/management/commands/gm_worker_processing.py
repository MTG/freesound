import gearman
from django.core.management.base import NoArgsCommand
from utils.audioprocessing.freesound_audio_processing import process
from django.conf import settings
from sounds.models import Sound

def task_process_sound(gearman_worker, gearman_job):
    sound_id = gearman_job.data
    print "Processing sound with id", sound_id
    result = process(Sound.objects.get(id=sound_id))
    print "\tsound: ", sound_id, "processing", "ok" if result else "failed"
    return str(result) 

class Command(NoArgsCommand):
    help = 'Run the sound processing worker'

    def handle(self, **options):
        gm_worker = gearman.GearmanWorker(settings.GEARMAN_JOB_SERVERS)
        gm_worker.register_task('process_sound', task_process_sound)
        gm_worker.work()