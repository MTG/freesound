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

from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render as django_render
from django.template import TemplateDoesNotExist
from django.template.response import TemplateResponse
from django.urls import reverse


def selected_frontend(request):
    # Get the name of the template engine from session variable or get the default tempalte engine name
    # Template engines are named with frontend name
    name = request.session.get(settings.FRONTEND_SESSION_PARAM_NAME, settings.FRONTEND_DEFAULT)
    if name not in [engine['NAME'] for engine in settings.TEMPLATES]:
        name = settings.FRONTEND_DEFAULT  # If provided engine name is not avialable, use default
    return name


def render(request, template_name, context=None, content_type=None, status=None, using=None):
    """
    This is a wrapper around Django's render function that we use to handle chosing which frontend to render.
    A session variable is used to store which frontend should be used. This wrapper calls Django's render function
    with the `using` parameter set to the template engine name corresponding to the specified frontend.
    If the template can't be found, then we try again but using the default frontend.

    What this ebhaviour achieves is that if a template is not found for a given frontend, then it is loaded from
    the defualt frontend. This is similar to what could be ahieved using the `DIRS` parameter of the template
    engines configuration but it is not exatcly the same. Using this wrapper, we make sure that templates from
    the different frontend will never be mixed (e.g. we make sure that we don't take `sounds.html` from one
    frontend and `base.html` from another).

    This wrapper is intented to be use while we implement the new frontend. Once the whole implementation
    process is finished and we don't need the two frontends to coexist anymore, then we can get rid of this
    wrapper.
    """

    # Get the name of the template engine/frontend
    name = selected_frontend(request)

    try:
        return django_render(request, template_name, context, content_type, status, using=name)
    except TemplateDoesNotExist:

        if name != settings.FRONTEND_DEFAULT:
            # If the required template does can't be found using the selected engine, try with the default engine
            return django_render(request, template_name, context, content_type, status, using=settings.FRONTEND_DEFAULT)
        else:
            # If the default engine was being used, then raise the exception normally
            raise


def using_frontend(request, frontend_name):
    """
    Util functin to check which frontend is being used.
    Returns True if `frontend_name` corresponds to the currently selecred frontend.
    """
    return selected_frontend(request) == frontend_name


def using_beastwhoosh(request):
    """
    Returns True if currently used frontend is Beast Whoosh
    """
    return using_frontend(request, settings.FRONTEND_BEASTWHOOSH)


def using_nightingale(request):
    """
    Returns True if currently used frontend is Nightingale
    """
    return using_frontend(request, settings.FRONTEND_NIGHTINGALE)


def defer_if_beastwhoosh(redirect_to_view):
    """
    Util decorator to be used in views which, when using Beast Whoosh frontend, should redirect to other views.
    If there are pages in which the 2 front-end require the use of 2 completely different views, this decorator
    can be used to point to the specific Beast Whoosh view. Use it as:

    @defer_if_beastwhoosh(new_view_func)
    def old_view(request):
        ...
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not using_beastwhoosh(request):
                return view_func(request, *args, **kwargs)
            else:
                return redirect_to_view(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def redirect_if_beastwhoosh(redirect_url_name='front-page', kwarg_keys=None, query_string=''):
    """
    Util decorator to be used in view which, when using Beast Whoosh frontend, should return an HTTP redirect to
    a new URL. A typical use case for this is two views whose functionality has been merged into a single one, or
    a URL path which changes when using Beast Whoosh.

    This decorator takes a view name as an argument to be passed to the `reverse()` function.
    If `kwarg_keys` is used, the arguments passed to the current request are also passed to the `reverse`
    function. `kwarg_keys` is used to select which arguments get passed and in which order (see example below).
    Finally, a `query_string` parameter can also be passed to be appended at the end of the URL.

    Usage examples:

    @redirect_if_beastwhoosh('front-page')
    def view(request, ...):
        ...
    > This will simply redirect to the front page (i.e. '/')

    @redirect_if_beastwhoosh('front-page', query_string='param=value&param2=value2')
    def view(request, ...):
        ...
    > This will redirect to the front page with the passed query string (i.e. '/?param=value&param2=value2'

    @redirect_if_beastwhoosh('sound', kwarg_keys=['username', 'sound_id'], query_string='edit=1')
    def sound_edit(request, username, sound_id):
        ...
    > This will redirect to the 'sound' URL passing as arguments 'username' and 'sound_id', and adding the query
      string 'edit=1' (i.e. '/people/<username>/sounds/<sound_id>/?edit=1').

    This can be useful in cases where a specific feature has been moved to a different page. For example, in Beast
    Whoosh the list of followers is not displayed in a 'followers page' but as a modal that is shown after clicking
    a button in the user profile page. Therefore, if someone uses the old url for the followers page, it will need to
    be redirected to the profile page. The query string can be used in the new profile page to automatically open
    the followers modal if needed.
    """

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not using_beastwhoosh(request):
                return view_func(request, *args, **kwargs)
            else:
                if kwarg_keys is not None:
                    new_args = [kwargs[key] for key in kwarg_keys]
                else:
                    new_args = []
                url = reverse(redirect_url_name, args=new_args)
                if query_string:
                    url += f'?{query_string}'
                return HttpResponseRedirect(url)
        return _wrapped_view
    return decorator


def redirect_if_beastwhoosh_inline(function=None, redirect_url_name='front-page', kwarg_keys=None, query_string=''):
    """
    Works the same as redirect_if_beastwhoosh but can be used inline in urls.py url<>view definitions:

    > redirect_if_beastwhoosh_inline(PasswordResetView.as_view(form_class=FsPasswordResetForm))
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not using_beastwhoosh(request):
                return view_func(request, *args, **kwargs)
            else:
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


class BwCompatibleTemplateResponse(TemplateResponse):

    @property
    def rendered_content(self):
        """
        This is a customized version of TemplateResponse required for compatibility with the co-existence of the two
        front ends. Class-based views do not use the "render" shortcut to render the templates, so we can not use our
        customized "render" shortcut (see above in this file) which selects the right frontend according to the
        request and defaults to old frontend if template not found. We re-implement the same logic here, in the
        BwCompatibleTemplateResponse class which must be used in Class-based views if we want them to be compatible
        with BW frontend. As an example use of this class, see donations.views.DonationsList. Once we remove the old
        interface, we'll be able to get rid of these helper methods.
        """
        name = selected_frontend(self._request)
        self.using = name
        try:
            template = self.resolve_template(self.template_name)
        except TemplateDoesNotExist:
            if name != settings.FRONTEND_DEFAULT:
                # If the required template does can't be found using the selected engine, try with the default engine
                self.using = settings.FRONTEND_DEFAULT
                template = self.resolve_template(self.template_name)
            else:
                # If the default engine was being used, then raise the exception normally
                raise
        context = self.resolve_context(self.context_data)
        content = template.render(context, self._request)
        return content
