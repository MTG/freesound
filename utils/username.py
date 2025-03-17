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


from django.contrib.auth.models import User
from accounts.models import OldUsername
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse


def get_user_from_username_or_oldusername(username):
    # Helper to get the user from a username that could have changed
    user = None
    try:
        user = User.objects.select_related('profile').get(username__iexact=username)
    except User.DoesNotExist:
        try:
            user = OldUsername.objects.get(username__iexact=username).user
        except OldUsername.DoesNotExist:
            pass
    return user


def get_user_or_404(username):
    # Helper to get the user from an username or raise 404
    user = get_user_from_username_or_oldusername(username)
    return user


def get_parameter_user_or_404(request):
    if request.parameter_user is None:
        raise Http404
    return request.parameter_user


def redirect_if_old_username(func):
    """
    This is a decorator to return redirects when accessing a URL with the username in the pattern and that usernames
    corresponds to an old username. We re-build the URL with the current username of that user and return a redirect.
    Note that we don't use this decorator in views with @login_required because we don't want to apply redirects to
    internal URL that require users being logged in. This is because there should not be public links pointing to
    internal URLs.
    """

    def inner(request, *args, **kwargs):
        if hasattr(request, 'parameter_user'):
            # If request.parameter_user already exists because it was added by some other decorator, reuse it
            user = request.parameter_user 
        else:
            # Otherwise get the corresponding user (considering OldUsernames) object or raise 404
            user = get_user_or_404(kwargs['username'])

        if user and kwargs['username'] != user.username:
            # If the the username is an old username of the user, do redirect
            kwargs['username'] = user.username

            return redirect(reverse(inner, args=args, kwargs=kwargs), permanent=True)

        # Save user object in the request so it can be used by the view and/or other decorators
        request.parameter_user = user
        return func(request, *args, **kwargs)

    return inner


def raise_404_if_user_is_deleted(func):
    """
    This is a decorator that will raise a 404 error if the corresponding user of the <username> part of the URL
    path is marked as being a deleted user. This is used in views that we don't want to show for a user that has been
    deleted but for which we have a DB object (i.e. an anonymized user).
    """

    def inner(request, *args, **kwargs):
        if hasattr(request, 'parameter_user'):
            # If request.parameter_user already exists because it was added by some other decorator, reuse it
            user = request.parameter_user
        else:
            # Otherwise get the corresponding user object (considering OldUsernames) or raise 404
            user = get_user_or_404(kwargs['username'])

        if user is None or user.profile.is_anonymized_user:
            raise Http404

        # Save user object in the request so it can be used by the view and/or other decorators
        request.parameter_user = user
        return func(request, *args, **kwargs)

    return inner
