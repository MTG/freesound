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


from django.core.management.base import BaseCommand

from sounds.models import Sound
from utils.tagrecommendation_utilities import get_id_of_last_indexed_sound, post_sounds_to_tagrecommendation_service


class Command(BaseCommand):
    args = ""
    help = (
        "Get the id of the last indexed sound in tag recommendation service and send tag information of the older ones"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            dest="all",
            default=False,
            help="Repost all sounds to tag recommendation even if they were already indexed",
        )

    def handle(self, *args, **options):
        if options["all"]:
            last_indexed_id = 0
        else:
            last_indexed_id = get_id_of_last_indexed_sound()

        print("Starting at id %i" % last_indexed_id)
        sound_qs = Sound.objects.filter(moderation_state="OK", processing_state="OK", id__gt=last_indexed_id).order_by(
            "id"
        )
        post_sounds_to_tagrecommendation_service(sound_qs)
