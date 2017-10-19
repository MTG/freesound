from django.template import loader
from django.http import HttpResponse
from django.conf import settings


def render(request, template_name, context=None, content_type=None, status=None, using=None):
    name = request.session.get(settings.FRONTEND_SESSION_PARAM_NAME, settings.FRONTEND_DEFAULT)
    if name not in settings.AVAILABLE_FRONTENDS:
        name = settings.FRONTEND_DEFAULT
    content = loader.render_to_string(template_name, context, request, using=name)
    return HttpResponse(content, content_type, status)
