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

from __future__ import print_function

from django.core.management.base import BaseCommand

from django.contrib.auth.models import User
import random

from django.db.models.signals import post_delete, pre_delete, pre_save, post_save
import sounds
import forum
import ratings
import datetime
import comments
import tickets
from django.db import connection


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


class Command(BaseCommand):
    help = "Delete most of the database to make it smaller"

    def add_arguments(self, parser):
        parser.add_argument(
            '-ev', '--extractor_version',
            action='store',
            dest='freesound_extractor_version',
            default='0.3',
            help='Only index sounds analyzed with specific Freesound Extractor version')


    def disconnect_signals(self):
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

        pre_delete.disconnect(sounds.models.on_delete_sound, sender=sounds.models.Sound)
        post_delete.disconnect(sounds.models.post_delete_sound, sender=sounds.models.Sound)
        post_delete.disconnect(comments.models.on_delete_comment, sender=comments.models.Comment)
        post_save.disconnect(tickets.models.create_ticket_message, sender=tickets.models.TicketComment)


    def delete_some_users(self, userids):
        print(datetime.datetime.now().isoformat())
        with connection.cursor() as cursor:
            cursor.execute("delete from sounds_download where user_id in %s", [tuple(userids)])
        print(datetime.datetime.now().isoformat())
        User.objects.filter(id__in=userids).delete()
        print(datetime.datetime.now().isoformat())

    def delete_sound_uploaders(self):
        """ Delete 90% of users who have uploaded sounds """
        print("Users with sounds")
        userids = User.objects.values_list('id', flat=True).filter(profile__num_sounds__gt=0)
        numusers = len(userids)
        print("num users with sounds: %s" % numusers)
        randusers = sorted(random.sample(userids, int(numusers*0.9)))
        ch = [c for c in chunks(randusers, 1000)]
        tot = len(ch)
        for i, c in enumerate(ch, 1):
            print("%s/%s" % (i, tot))
            self.delete_some_users(c)


    def delete_downloaders(self):
        userids = User.objects.values_list('id', flat=True).filter(profile__num_sounds=0)
        userids = list(userids)
        numusers = len(userids)
        print("num users: %s" % numusers)
        random.shuffle(userids)
        # Keep 120000 users, and delete the rest
        randusers = sorted(userids[:120000])
        ch = [c for c in chunks(randusers, 10000)]
        tot = len(ch)
        for i, c in enumerate(ch, 1):
            print("%s/%s" % (i, tot))
            self.delete_some_users(c)

    def handle(self,  *args, **options):
        self.disconnect_signals()
        #self.delete_sound_uploaders()
        self.delete_downloaders()

