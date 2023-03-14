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

import json
import logging
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from sounds.models import Sound

from utils.audioprocessing import color_schemes
from utils.audioprocessing.freesound_audio_processing import set_timeout_alarm, check_if_free_space, \
    FreesoundAudioProcessor, WorkerException, cancel_timeout_alarm


console_logger = logging.getLogger("console")


def regenerate_images_for_sound(sound_id):
    console_logger.info("Starting processing of sound (%s)" % json.dumps({
        'task_name': 'regenerate_sound_images', 'sound_id': sound_id}))
    set_timeout_alarm(settings.WORKER_TIMEOUT, f'Processing of sound {sound_id} timed out')
    start_time = time.time()
    try:
        check_if_free_space()
        result = FreesoundAudioProcessor(sound_id=sound_id) \
            .process(skip_previews=True, update_sound_processing_state_in_db=False)
        if result:
            console_logger.info("Finished processing of sound (%s)" % json.dumps(
                {'task_name': 'regenerate_sound_images', 'sound_id': sound_id, 'result': 'success',
                'work_time': round(time.time() - start_time)}))
        else:
            console_logger.info("Finished processing of sound (%s)" % json.dumps(
                {'task_name': 'regenerate_sound_images', 'sound_id': sound_id, 'result': 'failure',
                'work_time': round(time.time() - start_time)}))

    except WorkerException as e:
        console_logger.error("WorkerException while processing sound (%s)" % json.dumps(
            {'task_name': 'regenerate_sound_images', 'sound_id': sound_id, 'error': str(e),
            'work_time': round(time.time() - start_time)}))

    except Exception as e:
        console_logger.error("Unexpected error while processing sound (%s)" % json.dumps(
            {'task_name': 'regenerate_sound_images', 'sound_id': sound_id, 'error': str(e),
            'work_time': round(time.time() - start_time)}))

    cancel_timeout_alarm()
    return True



class Command(BaseCommand):

    help = 'Re-generate spectrogram and waveform images for all sounds. Do not update sound database processing state.'

    def add_arguments(self, parser):
        parser.add_argument('-l', action='store', dest='limit', type=int, default=None, help='Maximum number of sounds for which to re-generate images in one go')

    def handle(self, *args, **options):
        last_sound_id_data = {'last_sound_id': 0}
        state_file_path = os.path.join(settings.DATA_PATH, 'regenerate_sound_images_last_id.json')
        if not os.path.exists(state_file_path):
            json.dump(last_sound_id_data, open(state_file_path, 'w'))
        else:
            last_sound_id_data = json.load(open(state_file_path))

        remaining_sound_ids = Sound.objects.filter(id__gt=int(last_sound_id_data['last_sound_id'])).order_by('id').values_list('id', flat=True)[0:options['limit']]
        total = len(remaining_sound_ids)
        start_time = time.time()

        for count, sound_id in enumerate(remaining_sound_ids):
            output = regenerate_images_for_sound(sound_id)
            if output:
                last_sound_id_data['last_sound_id'] = sound_id
                json.dump(last_sound_id_data, open(state_file_path, 'w'))
            average_time_per_sound = (time.time() - start_time)/(count + 1)
            remaining_time = average_time_per_sound * (total - (count + 1))
            console_logger.info(f'[{count + 1}/{total}] Remaining time: {remaining_time/60/60} hours\n')

        