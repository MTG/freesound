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

from past.utils import old_div
from django.conf import settings
from django.core.management.base import BaseCommand

from sounds.models import Sound
import utils.audioprocessing.processing as audioprocessing
from utils.audioprocessing import color_schemes
import os


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('sound_ids', type=str, help='Comma-separated list of sound ids')

    def handle(self, *args, **options):
        sound_ids = [int(sid) for sid in options['sound_ids'].split(',')]
        sounds = Sound.objects.filter(id__in=sound_ids)
        BASE_DIR = os.path.join(settings.DATA_PATH, 'test_color_schemes')
        try:
            os.mkdir(BASE_DIR)
        except:
            pass

        html_output = '<html>'
        for sound in sounds:
            print(sound)
            html_output += f'<div><h3>{sound.id} - {sound.original_filename}</h3>' 
            wav_file = os.path.join(BASE_DIR, f'{sound.id}.wav')
            wav_file_st = os.path.join(BASE_DIR, f'{sound.id}.st.wav')

            if not os.path.exists(wav_file_st):
                if os.path.exists(sound.locations('path')):
                    audioprocessing.convert_using_ffmpeg(sound.locations('path'), wav_file)
                else:
                    audioprocessing.convert_using_ffmpeg(sound.locations('preview.LQ.ogg.path'), wav_file)
                audioprocessing.stereofy_and_find_info(settings.STEREOFY_PATH, wav_file, wav_file_st)

            for count, color_scheme in enumerate([color_schemes.FREESOUND2_COLOR_SCHEME, color_schemes.OLD_BEASTWHOOSH_COLOR_SCHEME, color_schemes.BEASTWHOOSH_COLOR_SCHEME]):
                width = 500
                height = 201
                fft_size = 2048
                waveform_filename = f'{sound.id}-{count}-wave.png'
                spectral_filename = f'{sound.id}-{count}-spec.jpg'
                waveform_path = os.path.join(BASE_DIR, waveform_filename)
                spectral_path = os.path.join(BASE_DIR, spectral_filename)
                audioprocessing.create_wave_images(wav_file_st, waveform_path, spectral_path, width, height, fft_size, color_scheme=color_scheme)
                html_output += f'<img src="{spectral_filename}"> <img src="{waveform_filename}">{count}<br>'
            html_output += '</div>'
            
        html_output += '</html>'
        fid = open(os.path.join(BASE_DIR, '_generated_images.html'), 'w')
        fid.write(html_output)
        fid.close()
