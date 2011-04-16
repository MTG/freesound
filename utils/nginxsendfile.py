from django.http import HttpResponse,Http404
from django.core.servers.basehttp import FileWrapper
from django.conf import settings

import os

def sendfile(path, attachment_name, secret_url = None):
    if not os.path.exists(path):
        raise Http404
    
    if settings.DEBUG:
        response = HttpResponse(FileWrapper(file(path, "rb")))
        response['Content-Length'] = os.path.getsize(path)
    else:
        response = HttpResponse()
        response['X-Accel-Redirect'] = secret_url

    response['Content-Type']="application/octet-stream"
    response['Content-Disposition'] = "attachment; filename=\"%s\"" % attachment_name
    
    return response