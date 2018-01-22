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
from django.core.urlresolvers import NoReverseMatch
from django.urls import reverse


def get_user_from_username_or_oldusername(username):
    # Helper to get the user from an username that could have changed
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
    if user == None:
        raise Http404
    return user


def redirect_if_old_username_or_404(func):
    """
    This is a decorator to return redirects when accessing a URL with the username in the pattern and that usernames
    corresonds to an old username. We re-build the URL with the current username of that user and return a redirect.
    Note that we don't use this decorator in views with @login_redirect because we don't want to apply redirects to
    internal URL that require users being logged in. This is because there should not be public links pointing to
    internal URLs.
    """
    def inner(request, *args, **kwargs):
        new_user = get_user_or_404(kwargs['username'])
        if kwargs['username'] != new_user.username:
            kwargs['username'] = new_user.username
            return redirect(reverse(inner, args=args, kwargs=kwargs), permanent=True)
        return func(request, *args, **kwargs)
    return inner


