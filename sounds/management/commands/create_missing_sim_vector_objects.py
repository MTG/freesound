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

from django.conf import settings

from sounds.models import Sound, SoundAnalysis, SoundSimilarityVector
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """Iterate over all similarity spaces and check if there are missing SoundSimilarityVector objects that
     should have been created in the "process analysis results" task but that are not there. If vectors are missing
     and the corresponding analyzer data is available, the SoundSimilarityVector objects will be created.
    """

    def handle(self, *args, **options):
        self.log_start()

        results_per_space = {}
        for similarity_space_name, similarity_space in settings.SIMILARITY_SPACES.items():
            analyzer_name = similarity_space["analyzer"]
            sids_analyzer_ok = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="OK").values_list(
                "sound_id", flat=True
            )
            sids_sim_vectors_ok = SoundSimilarityVector.objects.filter(
                similarity_space_name=similarity_space_name
            ).values_list("sound_id", flat=True)
            sids_missing = set(sids_analyzer_ok) - set(sids_sim_vectors_ok)
            n_loaded = 0
            for sound in Sound.objects.filter(id__in=sids_missing):
                n = sound.load_similarity_vector(similarity_space_name=similarity_space_name)
                n_loaded += n
            results_per_space[similarity_space_name] = {"missing": len(sids_missing), "loaded": n_loaded}

        console_logger.info(
            "Finished checking for missing similarity vectors. Number of missing vectors created per similarity space: %s",
            results_per_space,
        )
        self.log_end(results_per_space)
