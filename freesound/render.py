from django.template import TemplateDoesNotExist
from django.conf import settings
from django.shortcuts import render as django_render


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

    # Get the name of the template engine from session variable or get the default tempalte engine name
    name = request.session.get(settings.FRONTEND_SESSION_PARAM_NAME, settings.FRONTEND_DEFAULT)
    if name not in [engine['NAME'] for engine in settings.TEMPLATES]:
        name = settings.FRONTEND_DEFAULT  # If provided engine name is not avialable, use default

    try:
        return django_render(request, template_name, context, content_type, status, using=name)
    except TemplateDoesNotExist:

        if name != settings.FRONTEND_DEFAULT:
            # If the required template does can't be found using the dselected engine, try with the default engine
            return django_render(request, template_name, context, content_type, status, using=settings.FRONTEND_DEFAULT)
        else:
            # If the default engine was being used, then raise the exception normally
            raise
