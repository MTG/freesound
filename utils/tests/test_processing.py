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

import os
from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from sounds.models import Sound
from utils.audioprocessing.freesound_audio_processing import FreesoundAudioProcessor, FreesoundAudioProcessorBeforeDescription
from utils.audioprocessing.processing import AudioProcessingException
from utils.sound_upload import get_processing_before_describe_sound_folder
from utils.test_helpers import create_test_files, create_user_and_sounds, \
    override_sounds_path_with_temp_directory, override_uploads_path_with_temp_directory, \
    override_previews_path_with_temp_directory, override_displays_path_with_temp_directory, \
    override_processing_tmp_path_with_temp_directory, override_processing_before_description_path_with_temp_directory


def convert_to_pcm_mock(input_filename, output_filename):
    return True


def convert_to_pcm_mock_create_file(input_filename, output_filename):
    create_test_files(paths=[output_filename], n_bytes=2048)
    return True


def convert_to_pcm_mock_fail(input_filename, output_filename):
    raise AudioProcessingException("failed converting to pcm")


def convert_using_ffmpeg_mock_fail(input_filename, output_filename, mono_out=False):
    raise AudioProcessingException("failed converting to pcm")


def stereofy_mock(stereofy_executble_path, input_filename, output_filename):
    return dict(
        duration=123.5,
        channels=2,
        samplerate=44100,
        bitdepth=16)


def stereofy_mock_fail(stereofy_executble_path, input_filename, output_filename):
    raise AudioProcessingException("stereofy has failed")


def convert_to_mp3_mock(input_filename, output_filename, quality):
    create_test_files(paths=[output_filename])


def convert_to_mp3_mock_fail(input_filename, output_filename, quality):
    raise AudioProcessingException("conversion to mp3 (preview) has failed")


def convert_to_ogg_mock(input_filename, output_filename, quality):
    create_test_files(paths=[output_filename])


def convert_to_ogg_mock_fail(input_filename, output_filename, quality):
    raise AudioProcessingException("conversion to ogg (preview) has failed")


def create_wave_images_mock(
        input_filename, output_filename_w, output_filename_s, image_width, image_height, fft_size, **kwargs):
    create_test_files(paths=[output_filename_w, output_filename_s])


def create_wave_images_mock_fail(
        input_filename, output_filename_w, output_filename_s, image_width, image_height, fft_size, **kwargs):
    raise AudioProcessingException("creation of display images has failed")


class AudioProcessingTestCase(TestCase):

    fixtures = ['licenses']

    def pre_test(self, create_sound_file=True):
        # Do some stuff which needs to be carried out right before each test
        self.assertEqual(self.sound.processing_state, "PE")
        if create_sound_file:
            create_test_files(paths=[f"{self.sound.locations('path')}"], make_valid_wav_files=True, duration=2)
    
    def setUp(self):
        user, _, sounds = create_user_and_sounds(num_sounds=1, type="wav")
        self.sound = sounds[0]
        self.user = user

    def test_sound_object_does_not_exist(self):
        with self.assertRaises(AudioProcessingException) as cm:
            FreesoundAudioProcessor(sound_id=999)
        exc = cm.exception
        self.assertIn('did not find Sound object', str(exc))

    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    def test_sound_path_does_not_exist(self):
        self.pre_test(create_sound_file=False)
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        self.assertFalse(result)  # Processing failed, retutned False
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "FA")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertIn('could not find file with path', self.sound.processing_log)
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @mock.patch('utils.audioprocessing.processing.convert_to_pcm', side_effect=convert_to_pcm_mock_fail)
    @mock.patch('utils.audioprocessing.processing.convert_using_ffmpeg', side_effect=convert_using_ffmpeg_mock_fail)
    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    def test_conversion_to_pcm_failed(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        # will fail because mocked version of convert_to_pcm fails
        self.assertFalse(result)  # Processing failed, retutned False
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "FA")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertIn('conversion to PCM failed', self.sound.processing_log)
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @mock.patch('utils.audioprocessing.processing.stereofy_and_find_info', side_effect=stereofy_mock_fail)
    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    def test_stereofy_failed(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        # processing will fail because stereofy mock raises an exception
        self.assertFalse(result)  # Processing failed, retutned False
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "FA")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertIn('stereofy has failed', self.sound.processing_log)
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    def test_set_audio_info_fields(self, *args):
        self.pre_test()
        FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.duration, 2.0)  # Assert that info properties were set
        self.assertEqual(self.sound.channels, 1)
        self.assertEqual(self.sound.samplerate, 44100)
        self.assertEqual(self.sound.bitrate, 0)
        self.assertEqual(self.sound.bitdepth, 16)

    @mock.patch('utils.audioprocessing.processing.convert_to_mp3', side_effect=convert_to_mp3_mock_fail)
    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    @override_previews_path_with_temp_directory
    def test_make_mp3_previews_fails(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        # processing will fail because convert_to_mp3 mock raises an exception
        self.assertFalse(result)  # Processing failed, retutned False
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "FA")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertIn('conversion to mp3 (preview) has failed', self.sound.processing_log)
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @mock.patch('utils.audioprocessing.processing.convert_to_ogg', side_effect=convert_to_ogg_mock_fail)
    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    @override_previews_path_with_temp_directory
    def test_make_ogg_previews_fails(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        # processing will fail because convert_to_ogg mock raises an exception
        self.assertFalse(result)  # Processing failed, retutned False
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "FA")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertIn('conversion to ogg (preview) has failed', self.sound.processing_log)
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @mock.patch('utils.audioprocessing.processing.create_wave_images', side_effect=create_wave_images_mock_fail)
    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    @override_previews_path_with_temp_directory
    @override_displays_path_with_temp_directory
    def test_create_images_fails(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id).process()
        # processing will fail because create_wave_images mock raises an exception
        self.assertFalse(result)  # Processing failed, retutned False
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "FA")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertIn('creation of display images has failed', self.sound.processing_log)
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    @override_previews_path_with_temp_directory
    @override_displays_path_with_temp_directory
    def test_skip_previews(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id)\
            .process(skip_previews=True)

        self.assertFalse(os.path.exists(self.sound.locations('preview.LQ.ogg.path')))
        self.assertFalse(os.path.exists(self.sound.locations('preview.HQ.ogg.path')))
        self.assertFalse(os.path.exists(self.sound.locations('preview.LQ.mp3.path')))
        self.assertFalse(os.path.exists(self.sound.locations('preview.HQ.mp3.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.spectral.M.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.spectral_bw.M.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.spectral.L.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.spectral_bw.L.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.wave.M.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.wave_bw.M.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.wave.L.path')))
        self.assertTrue(os.path.exists(self.sound.locations('display.wave_bw.L.path')))

        self.assertTrue(result)  # Processing succeeded
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "OK")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)

    @override_settings(USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING=False)
    @override_processing_tmp_path_with_temp_directory
    @override_sounds_path_with_temp_directory
    @override_previews_path_with_temp_directory
    @override_displays_path_with_temp_directory
    def test_skip_displays(self, *args):
        self.pre_test()
        result = FreesoundAudioProcessor(sound_id=Sound.objects.first().id) \
            .process(skip_displays=True)

        self.assertTrue(os.path.exists(self.sound.locations('preview.LQ.ogg.path')))
        self.assertTrue(os.path.exists(self.sound.locations('preview.HQ.ogg.path')))
        self.assertTrue(os.path.exists(self.sound.locations('preview.LQ.mp3.path')))
        self.assertTrue(os.path.exists(self.sound.locations('preview.HQ.mp3.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.spectral.M.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.spectral_bw.M.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.spectral.L.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.spectral_bw.L.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.wave.M.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.wave_bw.M.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.wave.L.path')))
        self.assertFalse(os.path.exists(self.sound.locations('display.wave_bw.L.path')))

        self.assertTrue(result)  # Processing succeeded
        self.sound.refresh_from_db()
        self.assertEqual(self.sound.processing_state, "OK")
        self.assertEqual(self.sound.processing_ongoing_state, "FI")
        self.assertFalse(len(os.listdir(settings.PROCESSING_TEMP_DIR)), 0)


class AudioProcessingBeforeDescriptionTestCase(TestCase):

    fixtures = ['licenses']

    def setUp(self):
        user, _, sounds = create_user_and_sounds(num_sounds=1, type="wav")
        self.sound = sounds[0]
        self.user = user

    @override_processing_tmp_path_with_temp_directory
    @override_processing_before_description_path_with_temp_directory
    @override_uploads_path_with_temp_directory
    def test_process_before_description(self):
        for filename in ['test_file.wav', 'test_filè2.wav']:
            uploaded_file_path = os.path.join(settings.UPLOADS_PATH, str(self.user.id), filename)
            create_test_files(paths=[uploaded_file_path], make_valid_wav_files=True, duration=2)
            result = FreesoundAudioProcessorBeforeDescription(audio_file_path=uploaded_file_path).process()
            self.assertTrue(result)
            self.assertListEqual(sorted(os.listdir(get_processing_before_describe_sound_folder(uploaded_file_path))), 
                sorted(['wave.png', 'spectral.png', 'preview.ogg', 'preview.mp3', 'info.json']))
