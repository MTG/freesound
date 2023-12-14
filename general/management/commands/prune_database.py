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
import logging
import os
import random

from django.contrib.auth.models import User, Group
from django.contrib.admin.models import LogEntry
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.db.models.signals import post_delete, pre_delete, pre_save, post_save
from silk.models import Request
from accounts.models import DeletedUser, EmailBounce, GdprAcceptance, OldUsername, Profile, ResetEmailRequest, SameUser, UserDeletionRequest, UserEmailSetting, UserFlag
from apiv2.models import ApiV2Client
from donations.models import Donation
from forum.models import Subscription
from general.models import AkismetSpam
from messages.models import MessageBody
from oauth2_provider.models import AccessToken, Application, Grant, RefreshToken

import comments
import forum
import ratings
import sounds
from sounds.models import BulkUploadProgress, DeletedSound, Flag
import tickets
from tickets.models import Ticket, TicketComment
from utils.chunks import chunks

console_logger = logging.getLogger('console')




class Command(BaseCommand):
    help = "Delete most of the database to make it smaller for development, and anonymise it"

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--keep-downloaders',
            dest='downloaders',
            default=100000,
            type=int,
            help='The number of downloaders to keep')

        parser.add_argument(
            '-s', '--keep-sounds',
            dest='sounds',
            default=5000,
            type=int,
            help='Number of sounds to keep'
        )

    def disconnect_signals(self):
        """Disconnect django signals that update aggregate counts when items are modified. We re-compute
        these counts as a separate step"""
        post_save.disconnect(forum.models.update_num_threads_on_thread_insert, sender=forum.models.Thread)
        pre_save.disconnect(forum.models.update_num_threads_on_thread_update, sender=forum.models.Thread)
        pre_save.disconnect(forum.models.index_posts_on_thread_update, sender=forum.models.Thread)
        post_delete.disconnect(forum.models.update_last_post_on_thread_delete, sender=forum.models.Thread)
        pre_save.disconnect(forum.models.update_num_posts_on_save_if_moderation_changes, sender=forum.models.Post)
        post_save.disconnect(forum.models.update_num_posts_on_post_insert, sender=forum.models.Post)
        post_delete.disconnect(forum.models.update_thread_on_post_delete, sender=forum.models.Post)
        post_delete.disconnect(ratings.models.post_delete_rating, sender=ratings.models.SoundRating)
        post_save.disconnect(ratings.models.update_num_ratings_on_post_save, sender=ratings.models.SoundRating)

        post_delete.disconnect(sounds.models.update_num_downloads_on_delete, sender=sounds.models.Download)
        post_save.disconnect(sounds.models.update_num_downloads_on_insert, sender=sounds.models.Download)
        post_delete.disconnect(sounds.models.update_num_downloads_on_delete_pack, sender=sounds.models.PackDownload)
        post_save.disconnect(sounds.models.update_num_downloads_on_insert_pack, sender=sounds.models.PackDownload)

        pre_delete.disconnect(sounds.models.on_delete_sound, sender=sounds.models.Sound)
        post_delete.disconnect(sounds.models.post_delete_sound, sender=sounds.models.Sound)
        post_delete.disconnect(comments.models.on_delete_comment, sender=comments.models.Comment)
        post_save.disconnect(tickets.models.create_ticket_message, sender=tickets.models.TicketComment)

    def delete_some_users(self, userids):
        console_logger.info(f'  Deleting {len(userids)} users')
        console_logger.info('   - downloads')
        # Do a bulk delete because it's faster than django deleting download rows individually for each user
        # TODO: This could be faster by making new download tables for only
        # the users that we are going to keep, and then remove the orignal
        # table and rename.
        with connection.cursor() as cursor:
            cursor.execute("delete from sounds_download where user_id in %s", [tuple(userids)])
            cursor.execute("delete from sounds_packdownloadsound where pack_download_id in (select id from sounds_packdownload where user_id in %s)", [tuple(userids)])
            cursor.execute("delete from sounds_packdownload where user_id in %s", [tuple(userids)])
        console_logger.info('   - done, user objects')
        User.objects.filter(id__in=userids).delete()
        console_logger.info('   - done')

    def delete_sound_uploaders(self, numkeep):
        """Delete users who have uploaded sounds, keeping at least `numkeep` sounds.
           Don't consider users who have uploaded more than 1000 sounds.
           Arguments:
              numkeep: the number of sounds to keep
        """
        console_logger.info('Deleting some uploaders')
        # If a user has more than this number of sounds then don't add them
        # (we want the number of users with sounds to be varied)
        max_number_of_sounds_per_user = 100
        users = User.objects.values_list('id', 'profile__num_sounds').filter(profile__num_sounds__gt=0)
        users = list(users)
        all_users_with_sounds = [u[0] for u in users]
        random.shuffle(users)
        numusers = len(users)
        console_logger.info(f'Number of uploaders: {numusers}')

        totalsounds = 0
        userids = []
        # Add random users until the number of total sounds is approximately `numkeep`
        for u, numsounds in users:
            if numsounds <= max_number_of_sounds_per_user:
                userids.append(u)
                totalsounds += numsounds
            if totalsounds > numkeep:
                break

        console_logger.info(f"Keeping {len(userids)} users with {totalsounds} sounds")
        
        users_not_in_userids = list(set(all_users_with_sounds) - set(userids))
        ch = [c for c in chunks(sorted(list(users_not_in_userids)), 1000)]
        tot = len(ch)
        for i, c in enumerate(ch, 1):
            console_logger.info(f' {i}/{tot}')
            self.delete_some_users(c)

    def delete_downloaders(self, numkeep):
        """Delete users who have only downloaded sounds
           Arguments:
               numkeep: the number of users to keep (all others are removed)
        """
        console_logger.info('Deleting some downloaders')
        userids = User.objects.values_list('id', flat=True).filter(profile__num_sounds=0)
        userids = list(userids)
        numusers = len(userids)
        console_logger.info(f'Number of downloaders: {numusers}')
        random.shuffle(userids)
        # Keep `numkeep` users, and delete the rest
        randusers = sorted(userids[numkeep:])
        ch = [c for c in chunks(randusers, 10000)]
        tot = len(ch)
        for i, c in enumerate(ch, 1):
            console_logger.info(f' {i}/{tot}')
            self.delete_some_users(c)

    def anonymise_database(self):
        users_to_update = []
        for user in User.objects.all():
            user.email = str(user.id) + '@freesound.org'
            user.first_name = ''
            user.last_name = ''
            # this password is 'freesound'
            user.password = 'pbkdf2_sha256$36000$PJRTmkaiwSEC$a8+HUj33133PZX7ToOuypT/CfLKNwMeJMXqBJ4QbQPg='
            user.is_staff = False
            user.is_superuser = False
            users_to_update.append(user)
        User.objects.bulk_update(users_to_update, ['email', 'first_name', 'last_name', 'password', 'is_staff', 'is_superuser'])

        MessageBody.objects.all().update(body='(message body) Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')
        TicketComment.objects.all().update(text='(ticket comment) Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.')

        GdprAcceptance.objects.all().update(date_accepted=datetime.datetime.now())
        
        Profile.objects.all().update(
            is_whitelisted=False,
            not_shown_in_online_users_list=False,
            last_stream_email_sent=None,
            last_attempt_of_sending_stream_email=None,
            is_adult=False,
            last_donation_email_sent=None,
            donations_reminder_email_sent=False,
        )

        # Bookmarks? Possibly set created to now()
        # Messages (link between 2 users)

        User.objects.all().update(last_login=datetime.datetime.now(), date_joined=datetime.datetime.now())
        for group in Group.objects.all():
            group.user_set.clear()

        Ticket.objects.filter(sender=None).delete()

    def delete_unneeded_tables(self):
        Session.objects.all().delete()
        AccessToken.objects.all().delete()
        Application.objects.all().delete()
        Grant.objects.all().delete()
        RefreshToken.objects.all().delete()
        OldUsername.objects.all().delete()
        ApiV2Client.objects.all().delete()
        DeletedUser.objects.all().delete()
        EmailBounce.objects.all().delete()
        ResetEmailRequest.objects.all().delete()
        SameUser.objects.all().delete()
        UserDeletionRequest.objects.all().delete()
        UserEmailSetting.objects.all().delete()
        UserFlag.objects.all().delete()

        LogEntry.objects.all().delete()
        Donation.objects.all().delete()
        # Forum
        Subscription.objects.all().delete()
        AkismetSpam.objects.all().delete()

        # Silk, deletes request, response, associated sql queries
        Request.objects.all().delete()

        BulkUploadProgress.objects.all().delete()
        DeletedSound.objects.all().delete()
        Flag.objects.all().delete()

    def handle(self, *args, **options):
        if os.environ.get('FREESOUND_PRUNE_DATABASE') != '1':
            raise Exception('Run this command with env FREESOUND_PRUNE_DATABASE=1 to confirm you want to prune the database')

        self.disconnect_signals()
        self.delete_unneeded_tables()
        # Delete downloaders first, this will remove the majority of the download table
        # so that when we delete uploaders, there are not as many download rows for other
        # users who have downloaded these uploaders' sounds
        self.delete_downloaders(options['downloaders'])
        self.delete_sound_uploaders(options['sounds'])
        self.anonymise_database()
        # Update counts
        call_command('report_count_statuses')
        call_command('set_first_post_in_threads')
