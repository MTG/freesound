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
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class CustomModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        """authenticate against case insensitive username or email

        In case there is an @ sign in the provided username field, it is likely that
        the user is trying to authenticate by providing an email+password pair (rather than
        username+password). In that case, we first try to authenticate using the email and
        if it does not succeed we try to authenticate using username. We do email first
        because it could happen that a_user.username == another_user.email (if a_user.username
        contains an @ and has email form). If that was the case, then another_user would not
        be able to login using email.
        """

        if "@" in username:
            # In this case, user is most probably using email+password pair to login
            # Try to get user object from email and check password
            try:
                user = User.objects.get(email__iexact=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                # If user was not found by email, it could be that user who's logging in has
                # '@' characters in username and therefore is trying normal username+password login
                pass

        # Do normal username+password login check
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass

        return None

    def get_user(self, user_id):
        """A custom get_user method which additionally selects the user profile in the same query.
        This means that most pages that check a field on the profile will no longer have to
        perform an additional query to get the profile."""
        try:
            user = UserModel._default_manager.select_related("profile", "gdpracceptance").get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
