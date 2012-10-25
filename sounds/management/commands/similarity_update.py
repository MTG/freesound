from django.core.management.base import BaseCommand
from sounds.models import Sound
from similarity.client import Similarity
from optparse import make_option

class Command(BaseCommand):
    help = "Take all sounds that haven't been added to the similarity service yet and add them. Use option --force to force reindex ALL sounds. Pas a number argument to limit the number of sounds that will be reindexed (to avoid collapsing similarity if using crons)"
    option_list = BaseCommand.option_list + (
    make_option('-f','--force',
        dest='force',
        action='store_true',
        default=False,
        help='Reindex all sounds regardless of their similarity state'),
    )

    def handle(self,  *args, **options):

        end = 100000000000 # Big enough numebr so num_sounds will never exceed this one
        if args:
            limit = args[0]
            if limit:
                end = int(limit)
            print "Indexing sounds to similarity (limit %i)"%end

        if options['force']:
            to_be_added = Sound.objects.filter(analysis_state='OK', moderation_state='OK')[0:end]
        else:
            to_be_added = Sound.objects.filter(analysis_state='OK', similarity_state='PE', moderation_state='OK')[0:end]

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

