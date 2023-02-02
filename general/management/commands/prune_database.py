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


import logging
import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models.signals import post_delete, pre_delete, pre_save, post_save

import comments
import forum
import ratings
import sounds
import tickets

console_logger = logging.getLogger('console')


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Command(BaseCommand):
    help = "Delete most of the database to make it smaller"

    def add_arguments(self, parser):
        parser.add_argument(
            '-d', '--keep-downloaders',
            dest='downloaders',
            default=120000,
            type=int,
            help='The number of downloaders to keep')

        parser.add_argument(
            '-u', '-keep-uploaders',
            dest='uploaders',
            default=10,
            type=int,
            help='Percentage of uploaders to keep'
        )

    def disconnect_signals(self):
        """Disconnect django signals that update aggregate counts when items are modified. We re-compute
        these counts as a separate step"""
        post_save.disconnect(forum.models.update_num_threads_on_thread_insert, sender=forum.models.Thread)
        pre_save.disconnect(forum.models.update_num_threads_on_thread_update, sender=forum.models.Thread)
        post_delete.disconnect(forum.models.update_last_post_on_thread_delete, sender=forum.models.Thread)
        pre_save.disconnect(forum.models.update_num_posts_on_save_if_moderation_changes, sender=forum.models.Post)
        post_save.disconnect(forum.models.update_num_posts_on_post_insert, sender=forum.models.Post)
        post_delete.disconnect(forum.models.update_last_post_on_post_delete, sender=forum.models.Post)
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
        console_logger.info('  Deleting {} users'.format(len(userids)))
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
        # This will delete some other related data, but it's not as slow as deleting downloads.
        # so we let django do it
        User.objects.filter(id__in=userids).delete()
        console_logger.info('   - done')

    def delete_sound_uploaders(self, pkeep):
        """Delete some percentage of users who have uploaded sounds
           Arguments:
              pkeep: the percentage of uploaders to keep
        """
        console_logger.info('Deleting some uploaders')
        userids = User.objects.values_list('id', flat=True).filter(profile__num_sounds__gt=0)
        numusers = len(userids)
        console_logger.info('Number of uploaders: {}'.format(numusers))
        percentage_remove = 1.0 - (pkeep / 100.0)
        randusers = sorted(random.sample(userids, int(numusers*percentage_remove)))
        ch = [c for c in chunks(randusers, 100)]
        tot = len(ch)
        for i, c in enumerate(ch, 1):
            console_logger.info(' {}/{}'.format(i, tot))
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
        console_logger.info('Number of downloaders: {}'.format(numusers))
        random.shuffle(userids)
        # Keep `numkeep` users, and delete the rest
        randusers = sorted(userids[numkeep:])
        ch = [c for c in chunks(randusers, 100000)]
        tot = len(ch)
        for i, c in enumerate(ch, 1):
            console_logger.info(' {}/{}'.format(i, tot))
            self.delete_some_users(c)

    def handle(self,  *args, **options):
        self.disconnect_signals()
        # Delete downloaders first, this will remove the majority of the download table
        # so that when we delete uploaders, there are not as many download rows for other
        # users who have downloaded these uploaders' sounds
        self.delete_downloaders(options['downloaders'])
        self.delete_sound_uploaders(options['uploaders'])

