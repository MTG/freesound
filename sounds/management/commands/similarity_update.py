from django.core.management.base import NoArgsCommand
from sounds.models import Sound
from similarity.client import Similarity
import time
import logging

class Command(NoArgsCommand):
    help = "Take all sounds that haven't been added to the similarity service yet and add them."

    def handle(self, **options):
        logger = logging.getLogger('web')
        t1 = time.time()
        to_be_added = Sound.objects.filter(analysis_state='OK', similarity_state='PE', moderation_state='OK')
        for sound in to_be_added:
            try:
                Similarity.add(sound.id, sound.locations('analysis.statistics.path'))
                #sound.similarity_state = 'OK'
                sound.set_similarity_state('OK')
                t2 = time.time()
                logger.info('similarity_update Duration: %s' % (t2-t1))
            except Exception, e:
                print 'Sound could not be added: \n\t%s' % str(e)
                #sound.similarity_state = 'FA'
                sound.set_similarity_state('FA')
            #sound.save()
