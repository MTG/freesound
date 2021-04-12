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
from django.db import models
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from sounds.models import License, Sound, Pack, Flag, DeletedSound, SoundOfTheDay, BulkUploadProgress


class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'deed_url', 'legal_code_url', 'change_order')

admin.site.register(License, LicenseAdmin)


class SoundAdmin(admin.ModelAdmin):
    fieldsets = ((None, {'fields': ('user', 'num_downloads' )}),
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
    search_fields = ('=id', '=user__username')
    readonly_fields = ('num_downloads', )
admin.site.register(Sound, SoundAdmin)


class DeletedSoundAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('sound_id', 'user_link', 'created')
    readonly_fields = ('data', 'sound_id', 'user')

    def get_queryset(self, request):
        # Override 'get_queryset' to optimize query by using select_related on appropriate fields
        qs = super(DeletedSoundAdmin, self).get_queryset(request)
        qs = qs.select_related('user')
        return qs

    def user_link(self, obj):
        if obj.user is None:
            return '-'
        return '<a href="{0}" target="_blank">{1}</a>'.format(
            reverse('admin:auth_user_change', args=[obj.user.id]),
            '{0}'.format(obj.user.username))

    user_link.allow_tags = True
    user_link.admin_order_field = 'user'
    user_link.short_description = 'User'

admin.site.register(DeletedSound, DeletedSoundAdmin)


class PackAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'name', 'created')
admin.site.register(Pack, PackAdmin)


class FlagAdmin(admin.ModelAdmin):
    raw_id_fields = ('reporting_user', 'sound')
    list_display = ('id', 'reporting_user_link', 'email_link', 'sound_link', 'sound_uploader_link', 'sound_is_explicit',
                    'reason_type', 'reason_summary', )
    list_filter = ('reason_type', 'sound__is_explicit')

    def get_queryset(self, request):
        # overrride 'get_queryset' to optimize query by using select_related on 'sound' and 'reporting_user'
        qs = super(FlagAdmin, self).get_queryset(request)
        qs = qs.select_related('sound', 'reporting_user')
        return qs

    def reporting_user_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(
            reverse('account', args=[obj.reporting_user.username]), obj.reporting_user.username) \
            if obj.reporting_user else '-'
    reporting_user_link.allow_tags = True
    reporting_user_link.admin_order_field = 'reporting_user__username'
    reporting_user_link.short_description = 'Reporting User'

    def email_link(self, obj):
        return '<a href="mailto:{0}" target="_blank">{1}</a>'.format(obj.email, obj.email) \
            if obj.email else '-'
    email_link.allow_tags = True
    email_link.admin_order_field = 'email'
    email_link.short_description = 'Email'

    def sound_uploader_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(reverse('account', args=[obj.sound.user.username]),
                                                              obj.sound.user.username)
    sound_uploader_link.allow_tags = True
    sound_uploader_link.admin_order_field = 'sound__user__username'
    sound_uploader_link.short_description = 'Uploader'

    def sound_link(self, obj):
        return '<a href="{0}" target="_blank">{1}</a>'.format(reverse('short-sound-link', args=[obj.sound_id]),
                                                              truncatechars(obj.sound.base_filename_slug, 50))
    sound_link.allow_tags = True
    sound_link.admin_order_field = 'sound__original_filename'
    sound_link.short_description = 'Sound'

    def reason_summary(self, obj):
        reason_no_newlines = obj.reason.replace('\n', '|')
        return truncatechars(reason_no_newlines, 100)

    def sound_is_explicit(self, obj):
        return obj.sound.is_explicit
    sound_is_explicit.short_description = 'Is Explicit'


admin.site.register(Flag, FlagAdmin)


class SoundOfTheDayAdmin(admin.ModelAdmin):
    raw_id_fields = ('sound',)
    list_display = ('date_display', 'sound', 'email_sent')
admin.site.register(SoundOfTheDay, SoundOfTheDayAdmin)


class BulkUploadProgressAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'created', 'progress_type', 'sounds_valid')
admin.site.register(BulkUploadProgress, BulkUploadProgressAdmin)
