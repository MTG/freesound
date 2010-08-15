from django.http import HttpResponse,Http404
from django.core.servers.basehttp import FileWrapper
from django.conf import settings

import os

def basic_sendfile(fname, download_name=None):
    if not os.path.exists(fname):
        raise Http404

    wrapper = FileWrapper(open(fname,"r"))

    response = HttpResponse(wrapper, content_type='application/octet-stream')
    response['Content-Length'] = os.path.getsize(fname)

    if download_name:
        response['Content-Disposition'] = "attachment; filename=%s" % download_name

    return response

def x_sendfile(fname, download_name=None):
    if not os.path.exists(fname):
        raise Http404

    response = HttpResponse('', content_type='application/octet-stream')
    response['Content-Length'] = os.path.getsize(fname)
    response['X-Accel-Redirect'] = fname

    if download_name:
        response['Content-Disposition'] = "attachment; filename=%s" % download_name

    return response

if getattr(settings,'SENDFILE',False) == 'x_sendfile':
    sendfile = x_sendfile
else:
    sendfile = basic_sendfile