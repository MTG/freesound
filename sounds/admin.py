# -*- coding: utf-8 -*-
from django.contrib import admin
from sounds.models import Download, License, Sound, Pack, Flag

class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'deed_url', 'legal_code_url', 'change_order')

admin.site.register(License, LicenseAdmin)


class SoundAdmin(admin.ModelAdmin):
    fieldsets = ((None, {'fields': ('user', )}),
                 ('Filenames', {'fields': ('original_path', 'base_filename_slug')}),
                 ('User defined fields', {'fields': ('description', 'license', 'original_filename', 'sources', 'pack')}),
                 ('File properties', {'fields': ('md5', 'type', 'duration', 'bitrate', 'bitdepth', 'samplerate', 'filesize', 'channels', 'date_recorded')}),
                 ('Moderation', {'fields': ('moderation_state', 'moderation_date', 'has_bad_description')}),
                 ('Processing', {'fields': ('processing_state', 'processing_date', 'processing_log')}),
                 )
    raw_id_fields = ('user', 'pack', 'sources')
    list_display = ('id', 'user', 'original_filename', 'license', 'created', 'moderation_state')
    list_filter = ('moderation_state', 'license', 'processing_state')

admin.site.register(Sound, SoundAdmin)

class PackAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'name', 'created')

admin.site.register(Pack, PackAdmin)


class FlagAdmin(admin.ModelAdmin):
    raw_id_fields = ('reporting_user', 'sound')
    list_display = ('reporting_user', 'email', 'reason_type')
admin.site.register(Flag, FlagAdmin)

class DownloadAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'pack', 'sound')
    list_display = ('user', 'created', 'sound', 'pack')

admin.site.register(Download, DownloadAdmin)
