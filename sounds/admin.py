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

from django.urls import re_path
from django.contrib import admin, messages
from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpResponseRedirect
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_object_actions import DjangoObjectActions

from sounds.models import License, Sound, Pack, Flag, DeletedSound, SoundOfTheDay, BulkUploadProgress, SoundAnalysis


@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    list_display = ('name', 'deed_url', 'legal_code_url', )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sound)
class SoundAdmin(DjangoObjectActions, admin.ModelAdmin):
    fieldsets = ((None, {'fields': ('user', 'num_downloads' )}),
                 ('Filenames', {'fields': ('get_filename',)}),
                 ('User defined fields', {'fields': ('description', 'license', 'original_filename', 'sources', 'pack')}),
                 ('File properties', {'fields': ('md5', 'type', 'duration', 'bitrate', 'bitdepth', 'samplerate',
                                                 'filesize', 'channels', 'date_recorded')}),
                 ('Moderation', {'fields': ('moderation_state', 'moderation_date', 'has_bad_description', 'is_explicit')}),
                 ('Processing', {'fields': ('processing_state', 'processing_date', 'processing_ongoing_state', 'processing_log', 'similarity_state')}),
                 )
    raw_id_fields = ('user', 'pack', 'sources')
    list_display = ('id', 'user', 'get_sound_name', 'created', 'moderation_state', 'get_processing_state')
    list_filter = ('moderation_state', 'processing_state')
    ordering = ['id']
    search_fields = ('=id', '=user__username')
    readonly_fields = ('num_downloads', )
    actions = ('reprocess_sound', )
    change_actions = ('reprocess_sound', )

    def has_add_permission(self, request):
        return False

    @admin.display(
        description='Processing state'
    )
    def get_processing_state(self, obj):
        processing_state = f'{obj.get_processing_state_display()}'
        ongoing_state_display = obj.get_processing_ongoing_state_display()
        if ongoing_state_display == 'Processing' or ongoing_state_display == 'Queued':
            processing_state += f' ({ongoing_state_display})'
        return processing_state

    @admin.display(
        description='Name'
    )
    def get_sound_name(self, obj):
        max_len = 15
        return f"{obj.original_filename[:max_len]}{'...' if len(obj.original_filename) > max_len else ''}"

    @admin.action(
        description='Re-process and re-analyze sounds'
    )
    def reprocess_sound(self, request, queryset_or_object):
        if isinstance(queryset_or_object, Sound):
            queryset_or_object.process(force=True, high_priority=True)
            messages.add_message(request, messages.INFO,
                                 f'Sound {queryset_or_object.id} was sent to re-process.')
        else:
            for sound in queryset_or_object:
                sound.process(force=True, high_priority=True)
            messages.add_message(request, messages.INFO,
                                 f'{queryset_or_object.count()} sounds were send to re-process.')

    def get_filename(self, obj):
        return obj.friendly_filename()

    reprocess_sound.label = 'Re-process sound'



@admin.register(DeletedSound)
class DeletedSoundAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('sound_id', 'user_link', 'created')
    readonly_fields = ('data', 'sound_id', 'user')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        # Override 'get_queryset' to optimize query by using select_related on appropriate fields
        qs = super().get_queryset(request)
        qs = qs.select_related('user')
        return qs

    @admin.display(
        description='User',
        ordering='user',
    )
    def user_link(self, obj):
        if obj.user is None:
            return '-'
        return mark_safe('<a href="{}" target="_blank">{}</a>'.format(
            reverse('admin:auth_user_change', args=[obj.user.id]),
            f'{obj.user.username}'))


@admin.register(Pack)
class PackAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'name', 'created')
    search_fields = ('=user__username', '=name', )

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    raw_id_fields = ('reporting_user', 'sound')
    list_display = ('id', 'reporting_user_link', 'email_link', 'sound_link', 'sound_uploader_link', 'sound_is_explicit',
                    'reason_type', 'reason_summary', )
    list_filter = ('reason_type', 'sound__is_explicit')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('sound', 'sound__user', 'reporting_user')
        return qs

    @admin.display(
        description='Reporting User',
        ordering='reporting_user__username',
    )
    def reporting_user_link(self, obj):
        return mark_safe('<a href="{}" target="_blank">{}</a>'.format(
            reverse('account', args=[obj.reporting_user.username]), obj.reporting_user.username)) \
            if obj.reporting_user else '-'

    @admin.display(
        description='Email',
        ordering='email',
    )
    def email_link(self, obj):
        return mark_safe(f'<a href="mailto:{obj.email}" target="_blank">{obj.email}</a>') \
            if obj.email else '-'

    @admin.display(
        description='Uploader',
        ordering='sound__user__username',
    )
    def sound_uploader_link(self, obj):
        return mark_safe('<a href="{}" target="_blank">{}</a>'.format(reverse('account', args=[obj.sound.user.username]),
                                                              obj.sound.user.username))

    @admin.display(
        description='Sound',
        ordering='sound__original_filename',
    )
    def sound_link(self, obj):
        return mark_safe('<a href="{}" target="_blank">{}</a>'.format(reverse('short-sound-link', args=[obj.sound_id]),
                                                              truncatechars(obj.sound.friendly_filename(), 50)))

    def reason_summary(self, obj):
        reason_no_newlines = obj.reason.replace('\n', '|')
        return truncatechars(reason_no_newlines, 100)

    @admin.display(
        description='Is Explicit'
    )
    def sound_is_explicit(self, obj):
        return obj.sound.is_explicit




@admin.register(SoundOfTheDay)
class SoundOfTheDayAdmin(admin.ModelAdmin):
    change_list_template = "admin_custom/sound_of_the_day_changelist.html"
    raw_id_fields = ('sound',)
    list_display = ('date_display', 'sound', 'email_sent')
    ordering = ('-date_display', )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            re_path('generate_new_sounds/', self.generate_new_sounds),
            re_path('clear_sound_of_the_day_cache/', self.clear_sound_of_the_day_cache),
        ]
        return my_urls + urls

    def generate_new_sounds(self, request):
        call_command('create_random_sounds')
        messages.add_message(request, messages.INFO, 'New random sounds of the dat have been generated!')
        return HttpResponseRedirect(reverse('admin:sounds_soundoftheday_changelist'))

    def clear_sound_of_the_day_cache(self, request):
        try:
            for key in cache.keys('*random_sound*'):
                cache.delete(key)
            messages.add_message(request, messages.INFO, 'Current cache for sound of the day has been cleared!')
        except AttributeError:
             messages.add_message(request, messages.WARNING, 'Could not empty cache for sound of the day as selected cache backend is not compatible')
        return HttpResponseRedirect(reverse('admin:sounds_soundoftheday_changelist'))

        



@admin.register(BulkUploadProgress)
class BulkUploadProgressAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)
    list_display = ('user', 'created', 'progress_type', 'sounds_valid')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SoundAnalysis)
class SoundAnalysisAdmin(DjangoObjectActions, admin.ModelAdmin):
    list_display = ('analyzer', 'sound_id',  'analysis_status', 'last_sent_to_queue', 'last_analyzer_finished',
                    'num_analysis_attempts', 'analysis_time')
    ordering = ('-last_analyzer_finished',)
    list_filter = ('analyzer', 'analysis_status')
    search_fields = ('=sound__id',)
    actions = ('re_run_analysis',)
    change_actions = ('re_run_analysis',)
    readonly_fields = []

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + \
               [field.name for field in obj._meta.fields] + \
               [field.name for field in obj._meta.many_to_many] + ['analysis_logs', 'analysis_data_file']

    def has_add_permission(self, request, obj=None):
        return False

    @admin.action(
        description='Re-run analysis with same analyzer'
    )
    def re_run_analysis(self, request, queryset_or_object):
        if isinstance(queryset_or_object, SoundAnalysis):
            queryset_or_object.re_run_analysis()
            messages.add_message(request, messages.INFO,
                                 'Sound {} was sent to re-analyze with analyzer {}.'
                                 .format(queryset_or_object.sound_id, queryset_or_object.analyzer))
        else:
            for sound_analysis in queryset_or_object:
                sound_analysis.re_run_analysis()
            messages.add_message(request, messages.INFO,
                                 f'{queryset_or_object.count()} sounds were send to re-analyze.')
    re_run_analysis.label = 'Re-run analysis'

    @admin.display(
        description='Analysis logs',
        ordering='Analysis logs',
    )
    def analysis_logs(self, obj):
        return obj.get_analysis_logs()

    @admin.display(
        description='Analysis data file',
        ordering='Analysis data file',
    )
    def analysis_data_file(self, obj):
        return obj.get_analysis_data_from_file()
