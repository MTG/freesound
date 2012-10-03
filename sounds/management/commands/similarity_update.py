from django.core.management.base import BaseCommand
from sounds.models import Sound
from similarity.client.similarity_client import Similarity
from optparse import make_option

class Command(BaseCommand):
    help = "Take all sounds that haven't been added to the similarity service yet and add them. Use option --force to force reindex ALL sounds"
    option_list = BaseCommand.option_list + (
    make_option('-f','--force',
        dest='force',
        action='store_true',
        default=False,
        help='Reindex all sounds regardless of their similarity state'),
    )

    def handle(self,  *args, **options):

        if options['force']:
            to_be_added = Sound.objects.filter(analysis_state='OK', moderation_state='OK')
        else:
            to_be_added = Sound.objects.filter(analysis_state='OK', similarity_state='PE', moderation_state='OK')

        for sound in to_be_added:
            try:
                Similarity.add(sound.id, sound.locations('analysis.statistics.path'))
                #sound.similarity_state = 'OK'
                sound.set_similarity_state('OK')
            except Exception, e:
                print 'Sound could not be added: \n\t%s' % str(e)
                #sound.similarity_state = 'FA'
                sound.set_similarity_state('FA')
            #sound.save()

