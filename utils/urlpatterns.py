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

from functools import wraps
from django.http import HttpResponseRedirect
from django.urls import reverse


def redirect_inline(function=None, redirect_url_name='front-page', kwarg_keys=None, query_string=''):
    """
    Redirects to a specific view, can be used inline when defining urlpatterns.

    > redirect_inline(PasswordResetView.as_view(form_class=FsPasswordResetForm))
    """

    def decorator(view_func):

        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if kwarg_keys is not None:
                new_args = [kwargs[key] for key in kwarg_keys]
            else:
                new_args = []
            url = reverse(redirect_url_name, args=new_args)
            if query_string:
                url += f'?{query_string}'
            return HttpResponseRedirect(url)

        return _wrapped_view

    return decorator(function)
