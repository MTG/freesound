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
import pickle
from functools import partial, wraps
from itertools import count

import numpy as np
import pysndfile

from django.conf import settings
from django.contrib.auth.models import User
from django.test.utils import override_settings

from sounds.models import Sound, Pack, License, SoundAnalysis, SoundSimilarityVector
from geotags.models import GeoTag
from tempfile import TemporaryDirectory
from utils.tags import clean_and_split_tags


def create_test_files(
    filenames=None, directory=None, paths=None, n_bytes=1024, make_valid_wav_files=False, duration=0.0
):
    """
    This function generates test files with random content and saves them in the specified directory.
    :param filenames: list of names for the files to generate
    :param directory: folder where to store the files
    :param paths: if provided, then files are created in the indicated paths regardless of filenames and directory args
    :param n_bytes: number of bytes of each generated file
    :param make_valid_wav_files: whether to create a valid wav file with noise
    :param duration: duration of the wav file in seconds if make_valid_wav_files is True
    """
    if paths is None:
        paths = [os.path.join(directory, filename) for filename in filenames]

    for path in paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not make_valid_wav_files:
            f = open(path, "wb")
            f.write(os.urandom(n_bytes))
            f.close()
        else:
            data = np.random.uniform(-1, 1, int(duration * 44100))
            scaled = np.int16(data / np.max(np.abs(data)) * 32767)
            pysndfile.sndio.write(path, scaled, format="wav", rate=44100)


sound_counter = count()  # Used in create_user_and_sounds to avoid repeating sound names


def create_user_and_sounds(
    num_sounds=1,
    num_packs=0,
    user=None,
    count_offset=0,
    bst_category="ss-n",
    tags=None,
    description=None,
    processing_state="PE",
    moderation_state="PE",
    type="wav",
    username="testuser",
):
    """Creates User, Sound and Pack objects useful for testing.

    A counter is used to make sound names unique as well as other fields like md5 (see `sound_counter` variable).
    NOTE: creating sounds requires License objects to exist in DB. Do that by making sure your test case loads
    'licenses' fixture, i.e. "fixtures = ['licenses']".

    Args:
        num_sounds (int): N sounds to generate.
        num_packs (int): N packs in which the sounds above will be grouped.
        user (User): user owner of the created sounds (if not provided, a new user will be created).
        count_offset (int): start counting sounds at X.
        bst_category (str or None): category code to be added to the sounds (all sounds will have the same category)
        tags (str or None): string of tags to be added to the sounds (all sounds will have the same tags).
        description (str or None): description to be added to the sounds (all sounds will have the same description).
        processing_state (str): processing state of the created sounds.
        moderation_state (str): moderation state of the created sounds.
        type (str): type of the sounds to be created (e.g. 'wav').

    Returns:
        (Tuple(User, List[Pack], List[Sound]): 3-element tuple containing the user owning the sounds,
            a list of the packs created and a list of the sounds created.
    """
    count_offset = count_offset + next(sound_counter)
    if user is None:
        user = User.objects.create_user(username, password="testpass", email=f"{username}@freesound.org")
    packs = list()
    for i in range(0, num_packs):
        pack = Pack.objects.create(user=user, name="Test pack %i" % (i + count_offset))
        packs.append(pack)
    sounds = list()
    for i in range(0, num_sounds):
        pack = None
        if packs:
            pack = packs[i % len(packs)]
        sound = Sound.objects.create(
            user=user,
            original_filename="Test sound %i" % (i + count_offset),
            license=License.objects.last(),
            bst_category=bst_category,
            description=description if description is not None else "",
            pack=pack,
            md5="fakemd5_%i" % (i + count_offset),
            type=type,
            processing_state=processing_state,
            moderation_state=moderation_state,
        )

        if tags is not None:
            sound.set_tags(clean_and_split_tags(tags))
        sounds.append(sound)
    if len(sounds) > 1:
        GeoTag.objects.create(sound=sounds[1], lon=1.0, lat=1.0, zoom=1)
    return user, packs, sounds


def create_consolidated_audio_descriptors_and_similarity_vectors_for_sound(sound):
    """Creates fake consolidated audio descriptors and similarity vectors for a given sound.

    Args:
        sound (Sound): Sound object for which to create the descriptors and vectors.
    """
    # Create fake consolidated audio descriptors
    # The value that the feature takes is the idx of the feature in the provided list of feature names
    SoundAnalysis.objects.create(
        sound=sound,
        analysis_status="OK",
        analyzer=settings.CONSOLIDATED_ANALYZER_NAME,
        analysis_data={
            feature_name: idx for idx, feature_name in enumerate(settings.AVAILABLE_AUDIO_DESCRIPTORS_NAMES)
        },
    )

    # Create fake similarity vectors
    # The vector values are just the sound ID repeated to fill the vector size
    for similarity_space_name, space_options in settings.SIMILARITY_SPACES.items():
        SoundSimilarityVector.objects.create(
            sound=sound,
            similarity_space_name=similarity_space_name,
            vector=[float(sound.id) for i in range(space_options["vector_size"])],
        )


def override_path_with_temp_directory(fun, settings_path_name):
    """
    Decorator that wraps a function inside two context managers which i) create a temporary directory; and ii) override
    a settings path to that temporary directory. When the wrapped function exits, the created temporary will be
    deleted and the settings override reverted. This will happen even if the function exists with an Exception. This
    is useful in unit tests which write files to disk and we want to make sure these are deleted after the test has
    finished running.

    Code adapted from: https://stackoverflow.com/a/25827070
    """

    @wraps(fun)
    def ret_fun(*args, **kwargs):
        with TemporaryDirectory() as tmpfolder:
            with override_settings(**{settings_path_name: tmpfolder}):
                return fun(*args, **kwargs)

    return ret_fun


override_uploads_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="UPLOADS_PATH"
)

override_csv_path_with_temp_directory = partial(override_path_with_temp_directory, settings_path_name="CSV_PATH")

override_avatars_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="AVATARS_PATH"
)

override_analysis_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="ANALYSIS_PATH"
)

override_sounds_path_with_temp_directory = partial(override_path_with_temp_directory, settings_path_name="SOUNDS_PATH")

override_previews_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="PREVIEWS_PATH"
)

override_displays_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="DISPLAYS_PATH"
)

override_processing_tmp_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="PROCESSING_TEMP_DIR"
)

override_processing_before_description_path_with_temp_directory = partial(
    override_path_with_temp_directory, settings_path_name="PROCESSING_BEFORE_DESCRIPTION_DIR"
)


def create_fake_perform_search_engine_query_results_tags_mode():
    # This returns utils.search.SearchResults which was pickled from a real query in a local freesound instance
    return pickle.loads(
        b'\x80\x04\x95_\x0c\x00\x00\x00\x00\x00\x00\x8c\x0cutils.search\x94\x8c\rSearchResults\x94\x93\x94)\x81\x94}\x94(\x8c\x04docs\x94]\x94}\x94(\x8c\x02id\x94J\x89;\x03\x00\x8c\x05score\x94G?\xf0\x00\x00\x00\x00\x00\x00\x8c\x0fn_more_in_group\x94K%\x8c\ngroup_docs\x94]\x94}\x94(\x8c\x02id\x94\x8c\x06211849\x94\x8c\x05score\x94G?\xf0\x00\x00\x00\x00\x00\x00ua\x8c\ngroup_name\x94\x8c\x1e13453_Echo machine guitar pack\x94ua\x8c\x06facets\x94}\x94\x8c\x04tags\x94]\x94(\x8c\x0ffield-recording\x94M\xa1\x07\x86\x94\x8c\x05noise\x94M\x86\x07\x86\x94\x8c\nelectronic\x94M\x0c\x07\x86\x94\x8c\x05voice\x94M\xc8\x05\x86\x94\x8c\x05metal\x94M8\x05\x86\x94\x8c\x04loop\x94M\x08\x05\x86\x94\x8c\x06effect\x94M\xf1\x04\x86\x94\x8c\x05sound\x94M\xe8\x04\x86\x94\x8c\x04bass\x94M\xd7\x03\x86\x94\x8c\x05water\x94M\xd2\x03\x86\x94\x8c\x04male\x94M\xd0\x03\x86\x94\x8c\x02fx\x94M\xc8\x03\x86\x94\x8c\x04drum\x94Mf\x03\x86\x94\x8c\x07ambient\x94MS\x03\x86\x94\x8c\x05synth\x94M\x0b\x03\x86\x94\x8c\x03sfx\x94M\xf5\x02\x86\x94\x8c\npercussion\x94M\xe6\x02\x86\x94\x8c\x08ambience\x94M\xc3\x02\x86\x94\x8c\x0bmultisample\x94M\xb5\x02\x86\x94\x8c\nmezzoforte\x94M\xb2\x02\x86\x94\x8c\x04beat\x94M\xac\x02\x86\x94\x8c\x05words\x94M\xa6\x02\x86\x94\x8c\x06female\x94M\x80\x02\x86\x94\x8c\x06glitch\x94Mw\x02\x86\x94\x8c\x08zoom-h2n\x94Md\x02\x86\x94\x8c\x06nature\x94MW\x02\x86\x94\x8c\x07machine\x94MA\x02\x86\x94\x8c\x06speech\x94M=\x02\x86\x94\x8c\x04kick\x94M9\x02\x86\x94\x8c\x06sci-fi\x94M.\x02\x86\x94\x8c\x05remix\x94M"\x02\x86\x94\x8c\x03hit\x94M\x1a\x02\x86\x94\x8c\x04door\x94M\xfe\x01\x86\x94\x8c\x03mix\x94M\xfe\x01\x86\x94\x8c\x0cexperimental\x94M\xf5\x01\x86\x94\x8c\x05birds\x94M\xe3\x01\x86\x94\x8c\x05close\x94M\xe3\x01\x86\x94\x8c\x10flexible-grooves\x94M\xdf\x01\x86\x94\x8c\nsoundscape\x94M\xd7\x01\x86\x94\x8c\x0bnon-vibrato\x94M\xd5\x01\x86\x94\x8c\x0bchordophone\x94M\xd2\x01\x86\x94\x8c\nindustrial\x94M\xd1\x01\x86\x94\x8c\x0bsynthesizer\x94M\xd1\x01\x86\x94\x8c\x0fmtc500-m002-s14\x94M\xc9\x01\x86\x94\x8c\x04wood\x94M\xc2\x01\x86\x94\x8c\x04game\x94M\xa8\x01\x86\x94\x8c\x06engine\x94M\xa5\x01\x86\x94\x8c\x07english\x94M\xa4\x01\x86\x94\x8c\x04dark\x94M\x99\x01\x86\x94\x8c\nsound-trip\x94M\x95\x01\x86\x94\x8c\x06horror\x94M\x91\x01\x86\x94\x8c\x06guitar\x94M\x86\x01\x86\x94\x8c\x05drone\x94M\x84\x01\x86\x94\x8c\x06impact\x94M\x82\x01\x86\x94\x8c\trecording\x94M\x80\x01\x86\x94\x8c\x08electric\x94M}\x01\x86\x94\x8c\x05click\x94M{\x01\x86\x94\x8c\x05space\x94Mz\x01\x86\x94\x8c\x06sample\x94Mv\x01\x86\x94\x8c\natmosphere\x94Mu\x01\x86\x94\x8c\x0belectronica\x94Mu\x01\x86\x94\x8c\x05short\x94Mn\x01\x86\x94\x8c\x04wind\x94Me\x01\x86\x94\x8c\x06puzzle\x94Mc\x01\x86\x94\x8c\x04bell\x94Mb\x01\x86\x94\x8c\x07whisper\x94Mb\x01\x86\x94\x8c\x11string-instrument\x94M_\x01\x86\x94\x8c\x06mumble\x94M]\x01\x86\x94\x8c\x08alphabet\x94M[\x01\x86\x94\x8c\x0cbrian-cimmet\x94M[\x01\x86\x94\x8c\x0ccelia-madeoy\x94M[\x01\x86\x94\x8c\tcrossword\x94M[\x01\x86\x94\x8c\x0cdaniel-feyer\x94M[\x01\x86\x94\x8c\rdoug-peterson\x94M[\x01\x86\x94\x8c\x08gridplay\x94M[\x01\x86\x94\x8c\x07letters\x94M[\x01\x86\x94\x8c\x0emalcolm-ingram\x94M[\x01\x86\x94\x8c\x07solving\x94M[\x01\x86\x94\x8c\x0estanley-newman\x94M[\x01\x86\x94\x8c\x05vocal\x94M[\x01\x86\x94\x8c\x07digital\x94MR\x01\x86\x94\x8c\x03owi\x94ML\x01\x86\x94\x8c\x05scary\x94ML\x01\x86\x94\x8c\tdistorted\x94MJ\x01\x86\x94\x8c\x05motor\x94MI\x01\x86\x94\x8c\x04flex\x94ME\x01\x86\x94\x8c\x08computer\x94MD\x01\x86\x94\x8c\x04wave\x94MD\x01\x86\x94\x8c\x06reverb\x94MC\x01\x86\x94\x8c\x03car\x94M@\x01\x86\x94\x8c\x03low\x94M@\x01\x86\x94\x8c\ndistortion\x94M=\x01\x86\x94\x8c\nmechanical\x94M=\x01\x86\x94\x8c\x0csound-design\x94M9\x01\x86\x94\x8c\x06tenuto\x94M9\x01\x86\x94\x8c\x05drums\x94M8\x01\x86\x94\x8c\x04name\x94M4\x01\x86\x94\x8c\nportuguese\x94M4\x01\x86\x94\x8c\x12iberian-portuguese\x94M2\x01\x86\x94\x8c\x05music\x94M1\x01\x86\x94\x8c\x04hard\x94M0\x01\x86\x94\x8c\x06techno\x94M0\x01\x86\x94\x8c\x05train\x94M-\x01\x86\x94\x8c\x05house\x94M*\x01\x86\x94\x8c\x06people\x94M\'\x01\x86\x94\x8c\x04bang\x94M&\x01\x86\x94\x8c\x08ambiance\x94M#\x01\x86\x94\x8c\x04city\x94M#\x01\x86\x94\x8c\x03pad\x94M"\x01\x86\x94\x8c\x05piano\x94M"\x01\x86\x94\x8c\x0bsoundeffect\x94M!\x01\x86\x94\x8c\x04open\x94M\x1e\x01\x86\x94\x8c\x04rain\x94M\x1b\x01\x86\x94\x8c\x08hardcore\x94M\x1a\x01\x86\x94\x8c\x04bird\x94M\x17\x01\x86\x94\x8c\x08metallic\x94M\x12\x01\x86\x94\x8c\x06rattle\x94M\x11\x01\x86\x94\x8c\x05steel\x94M\r\x01\x86\x94\x8c\x04deep\x94M\x0c\x01\x86\x94\x8c\x05glass\x94M\x08\x01\x86\x94\x8c\x04buzz\x94M\x03\x01\x86\x94\x8c\x04high\x94M\x03\x01\x86\x94\x8c\x05weird\x94M\x03\x01\x86\x94\x8c\x07plastic\x94M\x00\x01\x86\x94\x8c\x05foley\x94K\xff\x86\x94\x8c\x05alien\x94K\xfb\x86\x94\x8c\x06liquid\x94K\xfb\x86\x94\x8c\tprocessed\x94K\xfb\x86\x94\x8c\x05crowd\x94K\xfa\x86\x94\x8c\x07walking\x94K\xfa\x86\x94\x8c\x05loops\x94K\xf9\x86\x94\x8c\x04loud\x94K\xf4\x86\x94\x8c\x05layer\x94K\xf3\x86\x94\x8c\nmicrophone\x94K\xf0\x86\x94\x8c\x08touchpad\x94K\xee\x86\x94\x8c\tfootsteps\x94K\xed\x86\x94\x8c\x07kitchen\x94K\xec\x86\x94\x8c\x06street\x94K\xeb\x86\x94\x8c\x06rhythm\x94K\xea\x86\x94\x8c\x05songs\x94K\xe7\x86\x94\x8c\x07factory\x94K\xe6\x86\x94\x8c\x08woodwind\x94K\xe3\x86\x94\x8c\tchallenge\x94K\xe1\x86\x94\x8c\x06creepy\x94K\xe1\x86\x94\x8c\x07soundfx\x94K\xe1\x86\x94\x8c\taerophone\x94K\xe0\x86\x94\x8c\x05snare\x94K\xde\x86\x94\x8c\x05field\x94K\xda\x86\x94\x8c\tmachinery\x94K\xda\x86\x94\x8c\x05laser\x94K\xd9\x86\x94\x8c\x08abstract\x94K\xd8\x86\x94\x8c\x04boom\x94K\xd5\x86\x94\x8c\x07effects\x94K\xd5\x86\x94\x8c\x06forest\x94K\xd3\x86\x94\x8c\x03toy\x94K\xd1\x86\x94\x8c\x05human\x94K\xcd\x86\x94\x8c\x07traffic\x94K\xca\x86\x94\x8c\x07electro\x94K\xc9\x86\x94\x8c\x03bpm\x94K\xc7\x86\x94\x8c\x04drop\x94K\xc7\x86\x94\x8c\x07contact\x94K\xc6\x86\x94\x8c\thousehold\x94K\xc4\x86\x94\x8c\x05storm\x94K\xc4\x86\x94\x8c\x05crash\x94K\xc3\x86\x94\x8c\x05dance\x94K\xc3\x86\x94\x8c\x06trance\x94K\xbf\x86\x94\x8c\x06stereo\x94K\xbd\x86\x94\x8c\x04beep\x94K\xbc\x86\x94\x8c\x08keyboard\x94K\xbc\x86\x94\x8c\x06filter\x94K\xbb\x86\x94\x8c\x08sequence\x94K\xbb\x86\x94\x8c\x06spooky\x94K\xbb\x86\x94\x8c\x07monster\x94K\xba\x86\x94\x8c\x05waves\x94K\xba\x86\x94\x8c\x03h4n\x94K\xb8\x86\x94\x8c\nsound-tour\x94K\xb8\x86\x94\x8c\x03air\x94K\xb6\x86\x94\x8c\x05paper\x94K\xb6\x86\x94\x8c\x07samples\x94K\xb4\x86\x94\x8c\x07strange\x94K\xb4\x86\x94\x8c\x06gabber\x94K\xb2\x86\x94\x8c\x06scream\x94K\xae\x86\x94\x8c\x04film\x94K\xac\x86\x94\x8c\x04ring\x94K\xac\x86\x94\x8c\x07thunder\x94K\xac\x86\x94\x8c\nrepetition\x94K\xab\x86\x94\x8c\x05dirty\x94K\xaa\x86\x94\x8c\x05night\x94K\xaa\x86\x94\x8c\x06analog\x94K\xa9\x86\x94\x8c\x05phone\x94K\xa9\x86\x94\x8c\x07scratch\x94K\xa7\x86\x94\x8c\x0bdouble-bass\x94K\xa5\x86\x94\x8c\x06melody\x94K\xa5\x86\x94\x8c\x05smash\x94K\xa5\x86\x94\x8c\x04tool\x94K\xa5\x86\x94\x8c\x06animal\x94K\xa4\x86\x94\x8c\x05movie\x94K\xa4\x86\x94\x8c\x05kicks\x94K\xa3\x86\x94\x8c\x03gun\x94K\xa2\x86\x94\x8c\x06tribal\x94K\xa2\x86\x94es\x8c\x0chighlighting\x94}\x94\x8c\x1dnon_grouped_number_of_results\x94M\x98c\x8c\tnum_found\x94M\xbd$\x8c\x05start\x94K\x00\x8c\x08num_rows\x94K\x01\x8c\x06q_time\x94K\x81ub.'
    )
