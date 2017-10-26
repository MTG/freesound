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

from django import forms
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse

from wiki.models import Content, Page


def page(request, name):
    try:
        version = int(request.GET.get("version", -1))
    except:
        version = -1

    try:
        if version == -1:
            content = Content.objects.filter(page__name__iexact=name).select_related().latest()
        else:
            content = Content.objects.select_related().get(page__name__iexact=name, id=version)
    except Content.DoesNotExist:
        content = Content.objects.filter(page__name__iexact="blank").select_related().latest()

    return render(request, 'wiki/page.html', locals())


def editpage(request, name):
    if not (request.user.is_authenticated and request.user.has_perm('wiki.add_page')):
        raise Http404

    # the class for editing...
    class ContentForm(forms.ModelForm):
        title = forms.CharField(label='Page name', widget=forms.TextInput(attrs={'size': '100'}))
        body = forms.CharField(widget=forms.Textarea(attrs={'rows': '40', 'cols': '100'}))

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
            form = ContentForm(initial={"title": content.title, "body": content.body})
        except Content.DoesNotExist:
            form = ContentForm()

    return render(request, 'wiki/edit.html', locals())


def history(request, name):
    if not (request.user.is_authenticated and request.user.has_perm('wiki.add_page')):
        raise Http404

    try:
        page = Page.objects.get(name__iexact=name)
    except Page.DoesNotExist:
        raise Http404

    try:
        versions = Content.objects.filter(page=page).select_related()
    except Content.DoesNotExist:
        raise Http404

    if request.GET and "version1" in request.GET and "version2" in request.GET:
        import difflib
        version1 = Content.objects.select_related().get(id=request.GET.get("version1"))
        version2 = Content.objects.select_related().get(id=request.GET.get("version2"))

        diff = difflib.HtmlDiff(4, 55).make_table(version1.body.split("\n"), version2.body.split("\n"), "version %d" % version1.id, "version %d" % version2.id, True, 5)

    return render(request, 'wiki/history.html', locals())
