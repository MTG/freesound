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
from django.urls import reverse
from sounds.models import License, Sound, Pack, Flag, DeletedSound, SoundOfTheDay, BulkUploadProgress


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
    ordering = ['id']
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
    list_display = ('id', 'reporting_user_link', 'email_link', 'sound_uploader_link', 'sound_link', 'reason_summary', 'reason_type')
    list_filter = ('reason_type',)

    def reporting_user_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(
            reverse('account', args=[obj.reporting_user.username]), obj.reporting_user.username) \
            if obj.reporting_user else '-'
    reporting_user_link.allow_tags = True

    def email_link(self, obj):
        return '<a href="mailto:{0}" target="_blank">{1}</a>'.format(obj.email, obj.email) \
            if obj.email else '-'
    email_link.allow_tags = True

    def sound_uploader_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(reverse('account', args=[obj.sound.user.username]),
                                                              obj.sound.user.username)
    sound_uploader_link.allow_tags = True

    def sound_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(reverse('short-sound-link', args=[obj.sound_id]),
                                                              obj.sound_id)
    sound_link.allow_tags = True

    def reason_summary(self, obj):
        reason_no_newlines = obj.reason.replace('\n', '|')
        return reason_no_newlines if len(reason_no_newlines) < 50 else reason_no_newlines[:50] + '...'


admin.site.register(Flag, FlagAdmin)


class SoundOfTheDayAdmin(admin.ModelAdmin):
    raw_id_fields = ('sound',)
    list_display = ('date_display', 'sound', 'email_sent')
admin.site.register(SoundOfTheDay, SoundOfTheDayAdmin)


class BulkUploadProgressAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'created', 'progress_type', 'sounds_valid')
admin.site.register(BulkUploadProgress, BulkUploadProgressAdmin)
