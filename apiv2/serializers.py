# -*- coding: utf-8 -*-

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

from sounds.models import Sound, Pack
from ratings.models import Rating
from comments.models import Comment
from bookmarks.models import BookmarkCategory
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from rest_framework import serializers
from freesound.utils.tags import clean_and_split_tags
from freesound.utils.similarity_utilities import get_sounds_descriptors
from utils import prepend_base


###################
# SOUND SERIALIZERS
###################

DEFAULT_FIELDS_IN_SOUND_LIST = 'uri,url,license,user,pack'  # Separated by commas (None = all)
DEFAULT_FIELDS_IN_SOUND_DETAIL = None  # Separated by commas (None = all)
DEFAULT_FIELDS_IN_PACK_DETAIL = None  # Separated by commas (None = all)


class AbstractSoundSerializer(serializers.HyperlinkedModelSerializer):
    '''
    In this abstract class we define ALL possible fields that a sound object should serialize/deserialize.
    Inherited classes set the default fields that will be shown in each view, although those can be altered using
    the 'fields' request parameter.
    '''
    default_fields = None

    def __init__(self, *args, **kwargs):
        super(AbstractSoundSerializer, self).__init__(*args, **kwargs)
        requested_fields = self.context['request'].GET.get("fields", self.default_fields)
        if not requested_fields: # If parameter is in url but parameter is empty, set to default
            requested_fields = self.default_fields

        if requested_fields:
            allowed = set(requested_fields.split(","))
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)


    class Meta:
        model = Sound
        fields = ('id',
                  'uri',
                  'url',
                  'name',
                  'tags',
                  'description',
                  'geotag',
                  'created',
                  'license',
                  'type',
                  'channels',
                  'filesize',
                  'bitrate',
                  'bitdepth',
                  'duration',
                  'samplerate',
                  'user',
                  'pack',
                  'download',
                  'previews',
                  'images',
                  'num_downloads',
                  'avg_rating',
                  'num_ratings',
                  'ratings',
                  'num_comments',
                  'comments',
                  'similar_sounds',
                  'analysis',
                  'analysis_frames',
                  'analysis_stats',
                  )


    uri = serializers.SerializerMethodField('get_uri')
    def get_uri(self, obj):
        return prepend_base(reverse('apiv2-sound-instance', args=[obj.id]))

    url = serializers.SerializerMethodField('get_url')
    def get_url(self, obj):
        return prepend_base(reverse('sound', args=[obj.user.username, obj.id]))

    user = serializers.SerializerMethodField('get_user')
    def get_user(self, obj):
        return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]))

    name = serializers.SerializerMethodField('get_name')
    def get_name(self, obj):
        return obj.original_filename

    tags = serializers.SerializerMethodField('get_tags')
    def get_tags(self, obj):
        return [tagged.tag.name for tagged in obj.tags.select_related("tag").all()]

    license = serializers.SerializerMethodField('get_license')
    def get_license(self, obj):
        return obj.license.deed_url

    pack = serializers.SerializerMethodField('get_pack')
    def get_pack(self, obj):
        try:
            if obj.pack:
                return prepend_base(reverse('apiv2-pack-instance', args=[obj.pack.id]))
            else:
                return None
        except:
            return None

    previews = serializers.SerializerMethodField('get_previews')
    def get_previews(self, obj):
        return {
            'preview-hq-mp3': obj.locations("preview.HQ.mp3.url"),
            'preview-hq-ogg': obj.locations("preview.HQ.ogg.url"),
            'preview-lq-mp3': obj.locations("preview.LQ.mp3.url"),
            'preview-lq-ogg': obj.locations("preview.LQ.ogg.url"),
        }

    images = serializers.SerializerMethodField('get_images')
    def get_images(self, obj):
        return {
            'waveform_m': obj.locations("display.wave.M.url"),
            'waveform_l': obj.locations("display.wave.L.url"),
            'spectral_m': obj.locations("display.spectral.M.url"),
            'spectral_l': obj.locations("display.spectral.L.url"),
        }

    analysis = serializers.SerializerMethodField('get_analysis')
    def get_analysis(self, obj):
        # Fake implementation. Method implemented in subclasses
        return None

    analysis_frames = serializers.SerializerMethodField('get_analysis_frames')
    def get_analysis_frames(self, obj):
        return obj.locations('analysis.frames.url')

    analysis_stats = serializers.SerializerMethodField('get_analysis_stats')
    def get_analysis_stats(self, obj):
        return prepend_base(reverse('apiv2-sound-analysis', args=[obj.id]))

    similar_sounds = serializers.SerializerMethodField('get_similar_sounds')
    def get_similar_sounds(self, obj):
        return prepend_base(reverse('apiv2-similarity-sound', args=[obj.id]))

    download = serializers.SerializerMethodField('get_download')
    def get_download(self, obj):
        return prepend_base(reverse('apiv2-sound-download', args=[obj.id]))

    ratings = serializers.SerializerMethodField('get_ratings')
    def get_ratings(self, obj):
        return prepend_base(reverse('apiv2-sound-ratings', args=[obj.id]))

    avg_rating = serializers.SerializerMethodField('get_avg_rating')
    def get_avg_rating(self, obj):
        return obj.avg_rating/2

    comments = serializers.SerializerMethodField('get_comments')
    def get_comments(self, obj):
        return prepend_base(reverse('apiv2-sound-comments', args=[obj.id]))

    geotag = serializers.SerializerMethodField('get_geotag')
    def get_geotag(self, obj):
        if obj.geotag:
            return str(obj.geotag.lon) + " " + str(obj.geotag.lat)
        else:
            return None

class SoundListSerializer(AbstractSoundSerializer):

    def __init__(self, *args, **kwargs):
        self.default_fields = DEFAULT_FIELDS_IN_SOUND_LIST
        super(SoundListSerializer, self).__init__(*args, **kwargs)

    def get_analysis(self, obj):
        # Get descriptors from the view class (should have been requested before the serializer is invoked)
        try:
            return self.context['view'].sound_analysis_data[str(obj.id)]
        except Exception, e:
            return None


class SoundSerializer(AbstractSoundSerializer):

    def __init__(self, *args, **kwargs):
        self.default_fields = DEFAULT_FIELDS_IN_SOUND_DETAIL
        super(SoundSerializer, self).__init__(*args, **kwargs)

    def get_analysis(self, obj):
        # Get the sound descriptors from gaia
        try:
            descriptors = self.context['request'].GET.get('descriptors', [])
            if descriptors:
                return get_sounds_descriptors([obj.id],
                                              descriptors.split(','),
                                              self.context['request'].GET.get('normalized', '0') == '1',
                                              only_leaf_descriptors=True)[str(obj.id)]
            else:
                return {}
        except Exception, e:
            return None


##################
# USER SERIALIZERS
##################


class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('id',
                  'uri',
                  'url',
                  'username',
                  'date_joined',
                  'sounds',
                  'avatar')

    url = serializers.SerializerMethodField('get_url')
    def get_url(self, obj):
        return prepend_base(reverse('account', args=[obj.username]))

    uri = serializers.SerializerMethodField('get_uri')
    def get_uri(self, obj):
        return prepend_base(reverse('apiv2-user-instance', args=[obj.username]))

    sounds = serializers.SerializerMethodField('get_sounds')
    def get_sounds(self, obj):
        return prepend_base(reverse('apiv2-user-sound-list', args=[obj.username]))

    avatar = serializers.SerializerMethodField('get_avatar')
    def get_avatar(self, obj):
        if obj.profile.has_avatar:
            return obj.profile.locations()['avatar']['L']['url']
        else:
            return None


##################
# PACK SERIALIZERS
##################


class PackSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Pack
        fields = ('id',
                  'uri',
                  'url',
                  'description',
                  'created',
                  'name',
                  'sounds',
                  'num_downloads')

    url = serializers.SerializerMethodField('get_url')
    def get_url(self, obj):
        return prepend_base(reverse('pack', args=[obj.user.username, obj.id]))

    uri = serializers.SerializerMethodField('get_uri')
    def get_uri(self, obj):
        return prepend_base(reverse('apiv2-pack-instance', args=[obj.id]))

    sounds = serializers.SerializerMethodField('get_sounds')
    def get_sounds(self, obj):
        return prepend_base(reverse('apiv2-pack-sound-list', args=[obj.id]))


##################
# BOOKMARK SERIALIZERS
##################


class BookmarkCategorySerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = BookmarkCategory
        fields = ('url',
                  'name',
                  'sounds')

    url = serializers.SerializerMethodField('get_url')
    def get_url(self, obj):
        if obj.id != 0:
            return prepend_base(reverse('bookmarks-for-user-for-category', args=[obj.user.username, obj.id]))
        else:
            return prepend_base(reverse('bookmarks-for-user', args=[obj.user.username]))

    sounds = serializers.SerializerMethodField('get_sounds')
    def get_sounds(self, obj):
        if obj.id != 0:
            return prepend_base(reverse('apiv2-user-bookmark-category-sounds', args=[obj.user.username, obj.id]))
        else:
            return prepend_base(reverse('apiv2-user-bookmark-uncategorized', args=[obj.user.username]))

class CreateBookmarkSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=128, required=False, help_text='Not Required. Name you want to give to the category.')
    name = serializers.CharField(max_length=128, required=True, help_text='Required. Name you want to give to the bookmark.')
    sound_id = serializers.IntegerField(required=True, help_text='Required. Id of the sound.')


####################
# RATING SERIALIZERS
####################

class SoundRatingsSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Rating
        fields = ('user',
                  'rating',
                  'created')

    user = serializers.SerializerMethodField('get_user')
    def get_user(self, obj):
        return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]))

    rating = serializers.SerializerMethodField('get_rating')
    def get_rating(self, obj):
        if (obj.rating % 2 == 1):
            return float(obj.rating)/2
        else:
            return obj.rating/2


class CreateRatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(required=True, help_text='Required. Chose an integer rating between 0 and 5.')
    sound_id = serializers.IntegerField(required=True, help_text='Required. Id of the sound.')

    def validate_rating(self, attrs, source):
        value = attrs[source]
        if (value not in [0,1,2,3,4,5]):
            raise serializers.ValidationError('You have to introduce an integer value between 0 and 5')
        return attrs

####################
# COMMENTS SERIALIZERS
####################

class SoundCommentsSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Comment
        fields = ('user',
                  'comment',
                  'created')

    user = serializers.SerializerMethodField('get_user')
    def get_user(self, obj):
        return prepend_base(reverse('apiv2-user-instance', args=[obj.user.username]))



class CreateCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=True, help_text='Required. Chose an integer rating between 0 and 5.')
    sound_id = serializers.IntegerField(required=True, help_text='Required. Id of the sound.')


####################
# UPLOAD SERIALIZERS
####################

ALLOWED_EXTENSIONS = ['wav', 'aiff', 'aif', 'ogg', 'flac', 'mp3']


class UploadAudioFileSerializer(serializers.Serializer):
    audiofile = serializers.FileField(max_length=100, allow_empty_file=False, help_text='Must be in .wav, .aif, .flac, .ogg or .mp3 format.')

    def validate_audiofile(self, attrs, source):
        value = attrs[source]
        try:
            extension = value.name.split('.')[-1]
        except:
            extension = None

        if extension not in ALLOWED_EXTENSIONS or not extension:
            raise serializers.ValidationError('Uploaded file format not supported or not an audio file.')

        return attrs


class SoundDescriptionSerializer(serializers.Serializer):
    LICENSE_CHOICES = (
        ('Attribution', 'Attribution'),
        ('Attribution Noncommercial', 'Attribution Noncommercial'),
        ('Creative Commons 0', 'Creative Commons 0'),)

    upload_filename = serializers.CharField(max_length=512, help_text='Must match a filename from \'Not Yet Described Uploaded Audio Files\' resource.')
    name = serializers.CharField(max_length=512, required=False, help_text='Not required. Name you want to give to the sound (by default it will be the original filename).')
    tags = serializers.CharField(max_length=512, help_text='Separate tags with spaces. Join multi-word tags with dashes.')
    description = serializers.CharField(help_text='Textual description of the sound.')
    license = serializers.ChoiceField(choices=LICENSE_CHOICES, help_text='License for the sound. Must be one either \'Attribution\', \'Attribution Noncommercial\' or \'Creative Commons 0\'.')
    pack = serializers.CharField(help_text='Not required. Pack name (if there is no such pack with that name, a new one will be created).', required=False)
    geotag = serializers.CharField(max_length=100, help_text='Not required. Latitude, longitude and zoom values in the form lat,lon,zoom (ex: \'2.145677,3.22345,14\').', required=False)

    def validate_upload_filename(self, attrs, source):
        value = attrs[source]
        if 'not_yet_described_audio_files' in self.context:
            if value not in self.context['not_yet_described_audio_files']:
                raise serializers.ValidationError('Upload filename must match with a filename from \'Not Yet Described Uploaded Audio Files\' resource.')
        return attrs

    def validate_geotag(self, attrs, source):
        value = attrs[source]
        if not value:
            return attrs
        fails = False
        try:
            data = value.split(',')
        except:
            fails = True
        if len(data) != 3:
            fails = True
        try:
            float(data[0])
            float(data[1])
            int(data[2])
        except:
            fails = True
        if fails:
            raise serializers.ValidationError('Geotag should have the format \'float,float,integer\' (for latitude, longitude and zoom respectively)')
        else:
            # Check that ranges are corrent
            if float(data[0]) > 90 or float(data[0]) < -90:
                raise serializers.ValidationError('Latitude must be in the range [-90,90].')
            if float(data[1]) > 180 or float(data[0]) < -180:
                raise serializers.ValidationError('Longitude must be in the range [-180,180].')
            if int(data[2]) < 11:
                raise serializers.ValidationError('Zoom must be at least 11.')
        return attrs

    def validate_tags(self, attrs, source):
        value = attrs[source]
        tags = clean_and_split_tags(value)
        if len(tags) < 3:
            raise serializers.ValidationError('Your should at least have 3 tags...')
        elif len(tags) > 30:
            raise serializers.ValidationError('There can be maximum 30 tags, please select the most relevant ones!')

        return attrs


class UploadAndDescribeAudioFileSerializer(SoundDescriptionSerializer):
    audiofile = serializers.FileField(max_length=100, allow_empty_file=False, help_text='Must be in .wav, .aif, .flac, .ogg or .mp3 format.')

    def __init__(self, *args, **kwargs):
        super(UploadAndDescribeAudioFileSerializer, self).__init__(*args, **kwargs)
        self.fields.pop('upload_filename')

    def validate_audiofile(self, attrs, source):
        value = attrs[source]
        try:
            extension = value.name.split('.')[-1]
        except:
            extension = None
        if extension not in ALLOWED_EXTENSIONS or not extension:
            raise serializers.ValidationError('Uploaded file format not supported or not an audio file.')
        return attrs


########################
# SIMILARITY SERIALIZERS
########################

ALLOWED_ANALYSIS_EXTENSIONS = ['json']

class SimilarityFileSerializer(serializers.Serializer):
    analysis_file = serializers.FileField(max_length=100, allow_empty_file=False, help_text='Analysis file created with the latest freesound extractor. Must be in .json format.')

    def validate_analysis_file(self, attrs, source):
        value = attrs[source]
        try:
            extension = value.name.split('.')[-1]
        except:
            extension = None

        if extension not in ALLOWED_ANALYSIS_EXTENSIONS or not extension:
            raise serializers.ValidationError('Uploaded analysis file format not supported, must be .json.')

        return attrs