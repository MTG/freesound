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
import datetime
import glob
import logging
import random

import os
import time

from django.conf import settings

from freesound.celery import get_queues_task_counts
from sounds.models import Sound, SoundAnalysis
from utils.management_commands import LoggingBaseCommand


console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):

    help = """Checks if there are sounds that have not been analyzed by the analyzers defined in 
    settings.ANALYZERS_CONFIGURATION and send jobs to the analysis workers if needed. If there are already
    many pending analysis jobs in a specific queue, it will not tigger new ones. This command is expected to be run 
    periodically so that we send jobs to the analysis workers in a controlled way. Also this command is useful to
    clean some tmp analysis files that are not needed (converted files), and to re-trigger sound which failed
    analysis or analysis jobs for which the workers could never communicate an ending (for example if a worker
    was killed because of too much memory usage, this command will re-trigger analysis and clean the status)."""

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action="store_true",
            help="Using this jobs will not be triggered but only information printed on screen.")
        parser.add_argument(
            '--only-failed',
            action="store_true",
            help="With these option the command will not schedule any missing analysis sounds but will only"
                 "re-trigger failed jobs (if number of attempts is below --max-num-analysis-attempts).")
        parser.add_argument(
            '--max-num-analysis-attempts',
            dest='max_num_analysis_attempts',
            action="store",
            default=settings.ORCHESTRATE_ANALYSIS_MAX_NUM_ANALYSIS_ATTEMPTS,
            help="Maximum number of times to try a re-analysis when analyzer fails.")

    def handle(self, *args, **options):

        self.log_start()
        data_to_log = {}

        # First print some information about overall status
        n_sounds = Sound.objects.all().count()
        console_logger.info("{: >44} {: >11} {: >11} {: >11} {: >11} {: >11}".format(
            *['', '# ok |', '# failed |', '# skipped |', '# queued |', '# missing']))
        for analyzer_name in settings.ANALYZERS_CONFIGURATION.keys():
            ok = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="OK").count()
            sk = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="SK").count()
            fa = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="FA").count()
            qu = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="QU").count()

            missing = n_sounds - (ok + sk + fa + qu)
            # print one row per analyzer
            console_logger.info("{: >44} {: >11} {: >11} {: >11} {: >11} {: >11}".format(
                *[analyzer_name + ' |', '{0} |'.format(ok), '{0} |'.format(sk),
                  '{0} |'.format(fa), '{0} |'.format(qu), missing]))

            data_to_log[analyzer_name] = {
                'OK': ok,
                'SK': sk,
                'FA': fa,
                'QU': qu,
                'Missing': missing,
            }
        console_logger.info('')

        # Now go analyzer by analyzer, check the status of the queue and send some jobs to it if needed
        # We get information about the current status of the queue and put it in a dictionary with structure
        # {analyzer_name:current_num_messages_in_queue}
        # The number of messages in the queue is that returned by celery/rabbitmq, and might not be in sync with
        # the number of SoundAnalysis objects with status "QU" as sometimes workers fill fail to report back. This
        # is not an issue as here we only need an approximate number of messages in queue to avoid adding too many
        # objects to it. Later we deal with SoundAnalysis objects that are stuck with "QU" status but that are no
        # longer in the celery/rabbitmq queue
        queues_status = get_queues_task_counts()
        queues_status_dict = {item[0]: item[1] for item in queues_status}
        for analyzer_name in settings.ANALYZERS_CONFIGURATION.keys():
            console_logger.info(analyzer_name)
            num_jobs_in_queue = queues_status_dict.get(analyzer_name, None)
            if num_jobs_in_queue is None:
                # If we don't get information about the queue, it is better not to add anything to it so do nothing
                data_to_log[analyzer_name]['just_sent'] = 0
                console_logger.info('- Not adding any jobs as queue information could not be retrieved')
            else:
                max_num_in_jobs_for_analyzer = settings.ANALYZERS_CONFIGURATION[analyzer_name]\
                    .get('max_jobs_in_queue', settings.ORCHESTRATE_ANALYSIS_MAX_JOBS_PER_QUEUE_DEFAULT)
                num_jobs_to_add = max_num_in_jobs_for_analyzer - num_jobs_in_queue
                if num_jobs_to_add <= 0:
                    data_to_log[analyzer_name]['just_sent'] = 0
                    console_logger.info('- Not adding any jobs as queue already has more than '
                                        'the maximum allowed jobs (has {} jobs, max is {})'
                                        .format(num_jobs_in_queue, max_num_in_jobs_for_analyzer))
                else:
                    # First add sounds from the pool of sounds that have never been analyzed with the selected
                    # analyzer.
                    # NOTE: the code below is not very efficient as the queries involved can become very large with
                    # large lists of IDs to filer. This could probably be optimized with some raw SQL.
                    if options['only_failed']:
                        # When using the only-failed option, we never look at non-analyzed "missing" sounds
                        missing_sounds = Sound.objects.none()
                    else:
                        sounds_with_sa_object = list(
                            SoundAnalysis.objects.filter(analyzer=analyzer_name).values_list('id', flat=True))
                        missing_sounds = Sound.objects.exclude(id__in=sounds_with_sa_object) \
                                                      .order_by('id')[:num_jobs_to_add]
                    num_missing_sounds_to_add = missing_sounds.count()
                    data_to_log[analyzer_name]['just_sent'] = num_missing_sounds_to_add
                    console_logger.info('- Will add {} new jobs from sounds that have not been analyzed'
                                        .format(num_missing_sounds_to_add))
                    if not options['dry_run']:
                        for sound in missing_sounds:
                            sound.analyze_new(analyzer_name, verbose=False)

                    # After adding sounds from the first pool, check if there are still jobs that can be added and
                    # see if there are any sounds with failed analyses that should be re-scheduled
                    num_jobs_to_add = num_jobs_to_add - num_missing_sounds_to_add
                    if num_jobs_to_add:
                        ssaa = SoundAnalysis.objects.filter(
                            analyzer=analyzer_name, analysis_status="FA",
                            num_analysis_attempts__lt=options['max_num_analysis_attempts'])[:num_jobs_to_add]
                        data_to_log[analyzer_name]['just_sent_fa'] = ssaa.count()
                        console_logger.info('- Will add {} new jobs from sounds that previously failed analysis'
                                            .format(ssaa.count()))
                        if not options['dry_run']:
                            for sa in ssaa:
                                sa.re_run_analysis(verbose=False)
            console_logger.info('')

        # Now revise SoundAnalysis objects that have been stuck in QU status for some time and set them to Failed
        # status. Because we run orchestrate_analysis often and have maximum size for the queue, sounds should never
        # be in the queue for a long time. If that happens, the maximum queue size should be adjusted for that
        # analyzer by adding the property 'max_jobs_in_queue' to the corresponding analyzer in
        # settings.ANALYZERS_CONFIGURATION). Therefore, if a SoundAnalysis has been in QU state for a rather long time,
        # it should be marked as failed as the worker will most probably been killed (see below). The
        # orchestrate_analysis command will try to re-process these sounds at some point after being marked
        # as Failed. SoundAnalysis stuck in "QU" status can happen if the analysis worker gets killed and never
        # communicates back to freesound (by calling the process_analysis_results celery task) to update the
        # corresponding SoundAnalysis object.
        date_cutoff = \
            datetime.datetime.now() - datetime.timedelta(hours=settings.ORCHESTRATE_ANALYSIS_MAX_TIME_IN_QUEUED_STATUS)
        ssaa = SoundAnalysis.objects.filter(analysis_status="QU", last_sent_to_queue__lt=date_cutoff)
        data_to_log['jobs_moved_from_qu_to_fa'] = ssaa.count()
        console_logger.info('Will move {} SoundAnalysis objects from QU to FA state because of them being queued for '
                            'too long'.format(ssaa.count()))
        if not options['dry_run']:
            ssaa.update(analysis_status="FA")

        # Now remove pcm conversion files which are left in disk and have not been used for a while. We keep these
        # files in disk in case we need to re-analyze a file or analyze a file with different analyzers in a short
        # period of time and so we can reuse the converted file. However old files can be safely deleted and will
        # be recreated if needbe.
        wav_files_in_analysis_path = glob.glob(settings.ANALYSIS_NEW_PATH + '**/*.wav')
        files_to_remove = []
        for filepath in wav_files_in_analysis_path:
            datetime.datetime.strptime(time.ctime(), "%a %b %d %H:%M:%S %Y")
            modification_time = datetime.datetime.strptime(time.ctime(os.path.getmtime(filepath)), "%c")
            date_cutoff = \
                datetime.datetime.now() - datetime.timedelta(
                    hours=settings.ORCHESTRATE_ANALYSIS_MAX_TIME_CONVERTED_FILES_IN_DISK)
            if modification_time < date_cutoff:
                files_to_remove.append(filepath)
        data_to_log['converted_files_to_remove'] = len(files_to_remove)
        console_logger.info('Will remove {} converted PCM files because of them being in disk for '
                            'too long'.format(len(files_to_remove)))
        if not options['dry_run']:
            for filepath in files_to_remove:
                try:
                    os.remove(filepath)
                except:
                    pass

        console_logger.info('')
        self.log_end(data_to_log)
