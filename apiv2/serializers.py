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
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from rest_framework import serializers
from freesound.utils.tags import clean_and_split_tags
import yaml


###############
# GENERAL UTILS
###############

def prepend_base(rel):
    return "http://%s%s" % (Site.objects.get_current().domain, rel)


###################
# SOUND SERIALIZERS
###################

DEFAULT_FIELDS_IN_SOUND_LIST = 'url,uri,user,pack'  # Separated by commas (None = all)
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
                  'user',
                  'pack',
                  'num_downloads',
                  'channels',
                  'duration',
                  'samplerate',
                  'analysis')


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

    pack = serializers.SerializerMethodField('get_pack')
    def get_pack(self, obj):
        if obj.pack:
            return prepend_base(reverse('apiv2-pack-instance', args=[obj.pack.id]))
        else:
            return None

    analysis = serializers.SerializerMethodField('get_analysis')
    def get_analysis(self, obj):
        ### Gaia-based implementation
        try:
            return self.context['view'].sound_analysis_data[str(obj.id)]
        except Exception, e:
            return None
        ### File-based test implementation
        '''
        try:
            analysis = yaml.load(file(obj.locations('analysis.statistics.path')))
            return analysis['lowlevel']['spectral_centroid']['mean']
        except Exception, e:
            return None
        '''


class SoundListSerializer(AbstractSoundSerializer):

    def __init__(self, *args, **kwargs):
        self.default_fields = DEFAULT_FIELDS_IN_SOUND_LIST
        super(SoundListSerializer, self).__init__(*args, **kwargs)


class SoundSerializer(AbstractSoundSerializer):

    def __init__(self, *args, **kwargs):
        self.default_fields = DEFAULT_FIELDS_IN_SOUND_DETAIL
        super(SoundSerializer, self).__init__(*args, **kwargs)


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
                  'sounds')

    url = serializers.SerializerMethodField('get_url')
    def get_url(self, obj):
        return prepend_base(reverse('account', args=[obj.username]))

    uri = serializers.SerializerMethodField('get_uri')
    def get_uri(self, obj):
        return prepend_base(reverse('apiv2-user-instance', args=[obj.username]))

    sounds = serializers.SerializerMethodField('get_sounds')
    def get_sounds(self, obj):
        return prepend_base(reverse('apiv2-user-sound-list', args=[obj.username]))


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