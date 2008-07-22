# -*- coding: utf-8 -*-
from django.contrib import admin
from models import License, Sound, Pack, Report

class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'deed_url', 'legal_code_url')

admin.site.register(License, LicenseAdmin)


class SoundAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', 'pack', 'sources', 'geotag')
    list_display = ('id', 'user', 'original_filename', 'license')
    list_filter = ('processing_state', 'moderation_state', 'license')
    fieldsets = (
         (None, {'fields': ('user', 'created', 'modified')}),
         ('Filenames', {'fields': ('original_path', 'base_filename_slug')}),
         ('User defined fields', {'fields': ('description', 'license', 'geotag', 'original_filename', 'sources', 'pack')}),
         ('File properties', {'fields': ('md5', 'type', 'duration', 'bitrate', 'bitdepth', 'samplerate', 'filesize', 'channels')}),
         ('Moderation', {'fields': ('moderation_state', 'moderation_date', 'moderation_bad_description')}),
         ('Processing', {'fields': ('processing_state', 'processing_date', 'processing_log')}),
     )

admin.site.register(Sound, SoundAdmin)


class PackAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'name', 'created')

admin.site.register(Pack, PackAdmin)


class ReportAdmin(admin.ModelAdmin):
    raw_id_fields = ('reporting_user', 'sound')
    list_display = ('reporting_user', 'email', 'reason_type')
admin.site.register(Report, ReportAdmin)
