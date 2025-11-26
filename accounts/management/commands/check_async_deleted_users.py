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

from django.conf import settings
from django.utils import timezone

from accounts.models import UserDeletionRequest
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = (
        "Gets a list of users that should have been asynchronously deleted but that for some reason were not."
        "The list of users is made using UserDeletionRequest table."
    )

    def handle(self, *args, **options):
        self.log_start()

        # Get a list of all UserDeletionRequest that have status 'DELETION_REQUEST_STATUS_DELETION_TRIGGERED'
        # and that were were not updated in the last hour. The last hour check is to give some time to the async
        # deletion action to take place. Then check if users were indeed deleted
        user_ids_not_properly_deleted = []
        for user_deletion_request in UserDeletionRequest.objects.filter(
            status=UserDeletionRequest.DELETION_REQUEST_STATUS_DELETION_TRIGGERED,
            last_updated__lt=timezone.now() - datetime.timedelta(hours=settings.CHECK_ASYNC_DELETED_USERS_HOURS_BACK),
        ):
            if (
                user_deletion_request.user_to is not None
                and not user_deletion_request.user_to.profile.is_anonymized_user
            ):
                # Deletion action for that user was triggered but user was not deleted
                # We later log that case so admins can take action
                user_ids_not_properly_deleted.append(user_deletion_request.user_to_id)
            else:
                # User was indeed fully deleted or marked as anonymized, but for some reason UserDeletionRequest object
                # was not updated, we update it now
                user_deletion_request.status = UserDeletionRequest.DELETION_REQUEST_STATUS_USER_WAS_DELETED
                user_deletion_request.save()

        user_ids_not_properly_deleted = list(set(user_ids_not_properly_deleted))
        console_logger.info(
            "Found {} users that should have been deleted and were not".format(len(user_ids_not_properly_deleted))
        )
        for user_id in user_ids_not_properly_deleted:
            # It could be that there are several requests per user, just display info about the first one
            user_deletion_request = UserDeletionRequest.objects.filter(user_to_id=user_id).first()
            console_logger.info(
                '- User "{0}" with id {1} should have been deleted. Action: "{2}". Reason: "{3}".'.format(
                    user_deletion_request.user_to.username,
                    user_deletion_request.user_to.id,
                    user_deletion_request.triggered_deletion_action,
                    user_deletion_request.triggered_deletion_reason,
                )
            )

        self.log_end({"n_users_should_have_been_deleted": len(user_ids_not_properly_deleted)})
