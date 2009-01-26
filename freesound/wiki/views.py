# Create your views here.
from models import *
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext

def page(request, name):
    try:
        content = Content.objects.filter(page__name__iexact=name).select_related().latest()
    except Content.DoesNotExist:
        content = Content.objects.filter(page__name__iexact="empty").select_related().latest()
    
    return render_to_response('wiki/page.html', locals(), context_instance=RequestContext(request)) 

def editpage(request, name):
    if not (request.user.is_authenticated and request.user.has_perm('wiki.add_page')):
        raise Http404

    content = Content.objects.filter(page__name__iexact=name).select_related().latest()

    try:
        # edit page/content
        if request.method == "POST":
            form = Form()
            
            if form.is_valid():
                # save new version!
                return HttpResponseRedirect(reverse('wiki-page-edit', args=[name]))
        else:
            form = Form()
    except Content.DoesNotExist:
        # TODO: create a page
        pass

    return render_to_response('wiki/page.html', locals(), context_instance=RequestContext(request)) 