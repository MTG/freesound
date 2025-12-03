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
import pprint
from collections import defaultdict

from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.db.models.functions import Coalesce

from accounts.models import Profile
from forum.models import Post
from sounds.models import Download, Pack, PackDownload, Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = (
        "This command checks if 'count' properties of Profiles, Sounds and Packs and in sync with the actual "
        "number of existing objects (e.g. if pack.num_sounds equals pack.sounds.all().count(). If the number"
        "does not match, it updates the corresponding object (unless the option -n is provided)"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--no-changes",
            action="store_true",
            dest="no-changes",
            default=False,
            help="Using the option --no-changes the original objects will not be modified.",
        )
        parser.add_argument(
            "-d",
            "--skip-downloads",
            action="store_true",
            dest="skip-downloads",
            default=False,
            help="Using the option --skip-downloads the command will not checked for mismatched downloads "
            "(to save time).",
        )

    def handle(self, *args, **options):
        self.log_start()

        def report_progress(message, total, count, scale=10000):
            if count % scale == 0:
                console_logger.info(message % (total, 100 * float(count + 1) / total))

        mismatches_report = defaultdict(int)
        mismatches_object_ids = defaultdict(list)

        # IMPLEMENTATION NOTE: on the code below we iterate multiple times on Sounds, Packs and Users tables.
        # This is done in this way because due to our DB structure and the way that Django ORM works, if we annotate
        # counts from different tables in a single queryset (annotations that require SQL JOINs with more than one
        # table), the result we obtain is not the count that we want (see https://code.djangoproject.com/ticket/10060)
        # The easier solution for us is to do the queries individually for each kind of "count" that we want to
        # annotate.

        # Sounds
        total = Sound.objects.all().count()

        # Look at number of comments
        for count, sound in enumerate(
            Sound.objects.all().annotate(real_num_comments=Count("comments")).order_by("id").iterator()
        ):
            real_num_comments = sound.real_num_comments
            if real_num_comments != sound.num_comments:
                mismatches_report["Sound.num_comments"] += 1
                mismatches_object_ids["Sound.num_comments"].append(sound.id)
                sound.num_comments = real_num_comments
                if not options["no-changes"]:
                    sound.is_index_dirty = True
                    sound.save()
            report_progress("Checking number of comments in %i sounds... %.2f%%", total, count)

        # Look at number of ratings and average rating
        for count, sound in enumerate(
            Sound.objects.all()
            .annotate(real_num_ratings=Count("ratings"), real_avg_rating=Coalesce(Avg("ratings__rating"), 0.0))
            .order_by("id")
            .iterator()
        ):
            real_num_ratings = sound.real_num_ratings
            if real_num_ratings != sound.num_ratings:
                mismatches_report["Sound.num_ratings"] += 1
                mismatches_object_ids["Sound.num_ratings"].append(sound.id)
                sound.num_ratings = real_num_ratings
                sound.avg_rating = sound.real_avg_rating
                if not options["no-changes"]:
                    sound.is_index_dirty = True
                    sound.save()
            report_progress("Checking number and average of ratings in %i sounds... %.2f%%", total, count)

        # Look at number of downloads
        if not options["skip-downloads"]:
            for count, sound in enumerate(
                Sound.objects.all().annotate(real_num_downloads=Count("downloads")).order_by("id").iterator()
            ):
                real_num_downloads = sound.real_num_downloads
                if real_num_downloads != sound.num_downloads:
                    mismatches_report["Sound.num_downloads"] += 1
                    mismatches_object_ids["Sound.num_downloads"].append(sound.id)
                    sound.num_downloads = real_num_downloads
                    if not options["no-changes"]:
                        sound.is_index_dirty = True
                        sound.save()
                report_progress("Checking number of downloads in %i sounds... %.2f%%", total, count)

        # Packs
        total = Pack.objects.all().count()

        # Look at number of sounds
        for count, pack in enumerate(
            Pack.objects.all()
            .extra(
                select={
                    "real_num_sounds": """
                SELECT COUNT(U0."id") AS "count"
                FROM "sounds_sound" U0
                WHERE U0."pack_id" = ("sounds_pack"."id")
                AND U0."processing_state" = 'OK' AND U0."moderation_state" = 'OK'
            """
                }
            )
            .iterator()
        ):
            real_num_sounds = pack.real_num_sounds
            if real_num_sounds != pack.num_sounds:
                mismatches_report["Pack.num_sounds"] += 1
                mismatches_object_ids["Pack.num_sounds"].append(pack.id)
                pack.num_sounds = real_num_sounds
                if not options["no-changes"]:
                    pack.save()
            report_progress("Checking number of sounds in %i packs... %.2f%%", total, count)

        # Look at number of downloads
        if not options["skip-downloads"]:
            for count, pack in enumerate(
                Pack.objects.all().annotate(real_num_downloads=Count("downloads")).order_by("id").iterator()
            ):
                real_num_downloads = pack.real_num_downloads
                if real_num_downloads != pack.num_downloads:
                    mismatches_report["Pack.num_downloads"] += 1
                    mismatches_object_ids["Pack.num_downloads"].append(pack.id)
                    pack.num_downloads = real_num_downloads
                    if not options["no-changes"]:
                        pack.save()
                report_progress("Checking number of downloads in %i packs... %.2f%%", total, count)

        # Users
        potential_user_ids = set()
        potential_user_ids.update(Sound.objects.all().values_list("user_id", flat=True))  # Add ids of uploaders
        potential_user_ids.update(Post.objects.all().values_list("author_id", flat=True))  # Add ids of forum posters
        total = len(potential_user_ids)

        # Look at number of sounds
        for count, user in enumerate(
            User.objects.filter(id__in=potential_user_ids)
            .select_related("profile")
            .extra(
                select={
                    "real_num_sounds": """
                        SELECT COUNT(U0."id") AS "count"
                        FROM "sounds_sound" U0
                        WHERE U0."user_id" = ("auth_user"."id")
                        AND U0."processing_state" = 'OK' AND U0."moderation_state" = 'OK'
                    """
                }
            )
            .iterator()
        ):
            user_profile = user.profile
            real_num_sounds = user.real_num_sounds
            if real_num_sounds != user_profile.num_sounds:
                mismatches_report["User.num_sounds"] += 1
                mismatches_object_ids["User.num_sounds"].append(user.id)
                user_profile.num_sounds = real_num_sounds
                if not options["no-changes"]:
                    user_profile.save()
            report_progress("Checking number of sounds in %i users... %.2f%%", total, count)

        # Look at number of posts
        for count, user in enumerate(
            User.objects.filter(id__in=potential_user_ids)
            .select_related("profile")
            .annotate(
                real_num_posts=Count("posts"),
            )
            .order_by("id")
            .iterator()
        ):
            user_profile = user.profile
            real_num_posts = user.real_num_posts
            if real_num_posts != user_profile.num_posts:
                # Only moderated posts should count in profile.num_posts, therefore the fact that we reach this part of the
                # code does not mean profile.num_posts is wrong because the difference between real_num_posts and
                # profile.num_posts could be due to unmoderated posts being wrongly counted in the annotated query
                # Ideally we should filter out unmoderated post in the annotated Count(), but it is easier to do the
                # check here as this is a case that will rarely happen and filtering in an annotation is complex without
                # writing custom SQL.
                real_num_moderated_posts = user.posts.exclude(moderation_state="NM").count()
                if real_num_moderated_posts != user_profile.num_posts:
                    mismatches_report["User.num_posts"] += 1
                    mismatches_object_ids["User.num_posts"].append(user.id)
                    user_profile.num_posts = real_num_moderated_posts
                    if not options["no-changes"]:
                        user_profile.save()
            report_progress("Checking number of posts in %i users... %.2f%%", total, count)

        if not options["skip-downloads"]:
            total = User.objects.all().count()
            # Look at number of sound downloads for all active users
            # NOTE: a possible optimization here would be to first get user candidates that have downloaded sounds.
            # It seems like 1/8th of the users do not have downloaded sounds, so we could probably make this step last
            # for 1/8th less of the time. Nevertheless, because we only run this very occasionally and the performance
            # is not severely impacted when running, we decided that the optimization is probably not worth right now.
            # Same thing applies to pack downloads below.
            for count, user in enumerate(
                User.objects.filter(is_active=True)
                .select_related("profile")
                .annotate(
                    real_num_sound_downloads=Count("sound_downloads"),
                )
                .order_by("id")
                .iterator()
            ):
                user_profile = user.profile

                real_num_sound_downloads = user.real_num_sound_downloads
                if real_num_sound_downloads != user_profile.num_sound_downloads:
                    mismatches_report["User.num_sound_downloads"] += 1
                    mismatches_object_ids["User.num_sound_downloads"].append(user.id)
                    user_profile.num_sound_downloads = real_num_sound_downloads

                    if not options["no-changes"]:
                        user_profile.save()

                report_progress("Checking number of downloaded sounds in %i users... %.2f%%", total, count)

            # Look at number of pack downloads for all active users (see note above)
            for count, user in enumerate(
                User.objects.filter(is_active=True)
                .select_related("profile")
                .annotate(
                    real_num_pack_downloads=Count("pack_downloads"),
                )
                .order_by("id")
                .iterator()
            ):
                user_profile = user.profile

                real_num_pack_downloads = user.real_num_pack_downloads
                if real_num_pack_downloads != user_profile.num_pack_downloads:
                    mismatches_report["User.num_pack_downloads"] += 1
                    mismatches_object_ids["User.num_pack_downloads"].append(user.id)
                    user_profile.num_pack_downloads = real_num_pack_downloads

                    if not options["no-changes"]:
                        user_profile.save()

                report_progress("Checking number of downloaded packs in %i users... %.2f%%", total, count)

            # Look at counts of sounds/packs downloaded from a user (i.e. for a given profile, the number of times her sounds/packs
            # have been downloaded by other users)
            qs = Profile.objects.filter(num_sounds__gt=0).all().only("user_id")
            total = qs.count()
            for count, profile in enumerate(qs):
                real_num_user_sounds_downloads = Download.objects.filter(sound__user_id=profile.user_id).count()
                real_num_user_packs_downloads = PackDownload.objects.filter(pack__user_id=profile.user_id).count()

                if (
                    real_num_user_sounds_downloads != profile.num_user_sounds_downloads
                    or real_num_user_packs_downloads != profile.num_user_packs_downloads
                ):
                    if real_num_user_sounds_downloads != profile.num_user_sounds_downloads:
                        mismatches_report["User.num_user_sounds_downloads"] += 1
                        mismatches_object_ids["User.num_user_sounds_downloads"].append(profile.user_id)
                        profile.num_user_sounds_downloads = real_num_user_sounds_downloads

                    if real_num_user_packs_downloads != profile.num_user_packs_downloads:
                        mismatches_report["User.num_user_packs_downloads"] += 1
                        mismatches_object_ids["User.num_user_packs_downloads"].append(profile.user_id)
                        profile.num_user_packs_downloads = real_num_user_packs_downloads

                    profile.save()

                report_progress(
                    "Checking number of downloaded sounds and packs from %i users... %.2f%%", total, count, scale=1000
                )

        console_logger.info("Number of mismatched counts: ")
        console_logger.info("\n" + pprint.pformat(mismatches_report))
        console_logger.info("\n" + pprint.pformat(mismatches_object_ids))

        self.log_end(mismatches_report)
