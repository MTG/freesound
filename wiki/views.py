# Create your views here.
from django import forms
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from wiki.models import Content, Page

def page(request, name):
    try:
        content = Content.objects.filter(page__name__iexact=name).select_related().latest()
    except Content.DoesNotExist: #@UndefinedVariable
        content = Content.objects.filter(page__name__iexact="blank").select_related().latest()
    
    return render_to_response('wiki/page.html', locals(), context_instance=RequestContext(request)) 

def editpage(request, name):
    if not (request.user.is_authenticated() and request.user.has_perm('wiki.add_page')):
        raise Http404

    # the class for editing...
    class ContentForm(forms.ModelForm):
        title = forms.CharField(widget=forms.TextInput(attrs={'size': '100'}))
        body = forms.CharField(widget=forms.Textarea(attrs={'rows':'40', 'cols':'100'}))
        class Meta:
            model = Content
            exclude = ('author', 'page', "created")
    
    if request.method == "POST":
        form = ContentForm(request.POST)
        
        if form.is_valid():
            content = form.save(commit=False)
            content.page = Page.objects.get_or_create(name=name)[0]
            content.author = request.user
            content.save()
            return HttpResponseRedirect(reverse('wiki-page', args=[name]))
    else:
        try:
            # if the page already exists, load up the previous content
            content = Content.objects.filter(page__name__iexact=name).select_related().latest()
            form = ContentForm(initial={"title": content.title, "body":content.body})
        except Content.DoesNotExist: #@UndefinedVariable
            form = ContentForm()

    return render_to_response('wiki/edit.html', locals(), context_instance=RequestContext(request)) 