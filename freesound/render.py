from django.template import loader
from django.http import HttpResponse


def render(request, template_name, context=None, content_type=None, status=None, using=None):
    name = 'old_frontend'
    if request.session.get('new_frontend', False):
        name = 'new_frontend'
    content = loader.render_to_string(template_name, context, request, name)
    return HttpResponse(content, content_type, status)
