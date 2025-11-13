#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import logging
import time

from django.conf import settings
from django.utils import timezone

from sounds.models import SoundAnalysis, SoundSimilarityVector, Sound
from utils.management_commands import LoggingBaseCommand


console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):

    help = """Iterate over all sounds and generate consolidated SoundAnalysis objects and SoundSimilarityVector objects
    if needed.
    """

    def add_arguments(self, parser):

        # Add force flag to re-generate all objects even if they already exist
        parser.add_argument(
            '--force',
            action='store_true',
            dest='force',
            default=False,
            help='If set, consolidated analysis and similarity vectors will be re-generated even if they already exist.')
        
        parser.add_argument(
            '--limit',
            action='store',
            dest='limit',
            default=None,
            help='Maximum number of sounds to process. If not set, all sounds will be processed.')
        
        parser.add_argument(
            '--chunk-size',
            action='store',
            dest='chunk_size',
            default=100,
            help='Number of sounds to process in each chunk (default: 100).')
        

    def handle(self, *args, **options):
        self.log_start()

        sound_ids_to_process = Sound.objects.values_list('id', flat=True)
        if options['force'] is False:  
            # We remove IDs for which both consolidated analysis and similarity vectors already exist
            sound_ids_with_consolidated_analysis = set(SoundAnalysis.objects.filter(analyzer=settings.CONSOLIDATED_ANALYZER_NAME)
                                                    .values_list('sound_id', flat=True))
            sound_ids_with_similarity_vectors = set(SoundSimilarityVector.objects.all().values_list('sound_id', flat=True))
            sound_ids_to_process = [sid for sid in sound_ids_to_process
                                    if sid not in sound_ids_with_consolidated_analysis
                                    and sid not in sound_ids_with_similarity_vectors]
            
        if options['limit'] is not None:
            sound_ids_to_process = sound_ids_to_process[:int(options['limit'])]

        console_logger.info(f'Processing {len(sound_ids_to_process)} sounds to create consolidated analysis and similarity vectors.')
        chunk_size = int(options['chunk_size'])
        starttime = time.monotonic()
        total_done = 0
        N = len(sound_ids_to_process)

        for i in range(0, len(sound_ids_to_process), chunk_size):
            sound_ids = sound_ids_to_process[i:i+chunk_size]
            ss = Sound.objects.filter(id__in=sound_ids)
            
            # Clear data from all non-consolidated sound analysis objects related to these sounds
            ssaa = SoundAnalysis.objects.filter(sound__in=sound_ids).exclude(analyzer=settings.CONSOLIDATED_ANALYZER_NAME)
            ssaa.update(analysis_data={}) 

            # Generate consolidated analyses and load similarity vectors for the chunk of sounds
            consolidated_analyis_objects = []
            similarity_vector_objects = []
            for sound in ss:
                consolidated_analysis_data, tmp_analyzers_data= sound.consolidate_analysis(no_db_operations=True)
                
                consolidated_analyis_objects.append(SoundAnalysis(
                    sound_id=sound.id,
                    analyzer=settings.CONSOLIDATED_ANALYZER_NAME,
                    analysis_data=consolidated_analysis_data,
                    analysis_status = "OK",
                    last_analyzer_finished = timezone.now()
                ))

                for similarity_space_name, similarity_space in settings.SIMILARITY_SPACES.items():
                    analyzer_data = tmp_analyzers_data.get(similarity_space['analyzer'], {})
                    if not analyzer_data:
                        try:
                            sa = SoundAnalysis.objects.get(sound_id=sound.id, analyzer=similarity_space['analyzer'], analysis_status='OK')
                            analyzer_data = sa.get_analysis_data_from_file()
                        except SoundAnalysis.DoesNotExist:
                            continue
                    try:
                        sim_vector = analyzer_data[similarity_space['vector_property_name']]
                        sim_vector = [float(x) for x in sim_vector] 
                    except (IndexError, ValueError):
                        continue

                    if len(sim_vector) != similarity_space['vector_size']:
                        continue
                    
                    similarity_vector_objects.append(SoundSimilarityVector(
                        sound_id=sound.id,
                        similarity_space_name=similarity_space_name,
                        vector=sim_vector
                    ) )
                    
            # Now that we loaded all the data, create the db objcts in bulk
            SoundAnalysis.objects.bulk_create(consolidated_analyis_objects, ignore_conflicts=True)
            SoundSimilarityVector.objects.bulk_create(similarity_vector_objects, ignore_conflicts=True)

            total_done += chunk_size
            elapsed = time.monotonic() - starttime
            seconds_remaining = ((N - total_done) / total_done) * elapsed if total_done > 0 else 0
            time_ramaining_label = f"{seconds_remaining/60/60:.4f} hours" if seconds_remaining > 3600 else f"{seconds_remaining/60:.2f} minutes"
            console_logger.info(f'Processed {total_done}/{N} sounds. Time remaining: {time_ramaining_label} ({total_done/elapsed:.2f} sounds/second).')
            
        self.log_end()
