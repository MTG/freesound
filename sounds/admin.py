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

from django.contrib import admin
from sounds.models import License, Sound, Pack, Flag, DeletedSound, SoundOfTheDay


class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'deed_url', 'legal_code_url', 'change_order')

admin.site.register(License, LicenseAdmin)


class SoundAdmin(admin.ModelAdmin):
    fieldsets = ((None, {'fields': ('user', )}),
                 ('Filenames', {'fields': ('base_filename_slug',)}),
                 ('User defined fields', {'fields': ('description', 'license', 'original_filename', 'sources', 'pack')}),
                 ('File properties', {'fields': ('md5', 'type', 'duration', 'bitrate', 'bitdepth', 'samplerate',
                                                 'filesize', 'channels', 'date_recorded')}),
                 ('Moderation', {'fields': ('moderation_state', 'moderation_date', 'has_bad_description', 'is_explicit')}),
                 ('Processing', {'fields': ('processing_state', 'processing_date', 'processing_log', 'analysis_state',
                                            'similarity_state')}),
                 )
    raw_id_fields = ('user', 'pack', 'sources')
    list_display = ('id', 'user', 'original_filename', 'license', 'created', 'moderation_state')
    list_filter = ('moderation_state', 'license', 'processing_state')
admin.site.register(Sound, SoundAdmin)


class DeletedSoundAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('sound_id', 'user')
admin.site.register(DeletedSound, DeletedSoundAdmin)


class PackAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'name', 'created')
admin.site.register(Pack, PackAdmin)


class FlagAdmin(admin.ModelAdmin):
    raw_id_fields = ('reporting_user', 'sound')
    list_display = ('reporting_user', 'email', 'reason_type')
admin.site.register(Flag, FlagAdmin)


class SoundOfTheDayAdmin(admin.ModelAdmin):
    raw_id_fields = ('sound',)
    list_display = ('sound', 'email_sent')
admin.site.register(SoundOfTheDay, SoundOfTheDayAdmin)
