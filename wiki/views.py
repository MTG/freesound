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

from django.http import HttpResponseRedirect, Http404

from django.shortcuts import render 
from django.urls import reverse

from wiki.models import Content, Page
from wiki.forms import ContentForm


def page(request, name):
    try:
        version = int(request.GET.get("version", -1))
    except ValueError:
        version = None

    try:
        page = Page.objects.get(name__iexact=name)
    except Page.DoesNotExist:
        page = Page.objects.get(name__iexact="blank")
        version = None

    content = None
    if version:
        try:
            content = Content.objects.select_related().get(page=page, id=version)
        except Content.DoesNotExist:
            # If there is no content with this version we try and get the latest
            content = None

    if not content:
        try:
            content = Content.objects.select_related().filter(page=page).latest()
        except Content.DoesNotExist:
            # If there is still no content, then this page has no Content objects, return Blank
            content = Content.objects.filter(page__name__iexact="blank").select_related().latest()

    tvars = {'content': content,
             'name': name}
    return render(request, 'wiki/page.html', tvars)


def editpage(request, name):
    if not (request.user.is_authenticated and request.user.has_perm('wiki.add_page')):
        raise Http404

    FormToUse = ContentForm

    if request.method == 'POST':
        form = FormToUse(request.POST)

        if form.is_valid():
            content = form.save(commit=False)
            content.page, _ = Page.objects.get_or_create(name=name)
            content.author = request.user
            content.save()
            return HttpResponseRedirect(reverse('wiki-page', args=[name]))
    else:
        try:
            # if the page already exists, load up the previous content
            content = Content.objects.filter(page__name__iexact=name).select_related().latest()
            form = FormToUse(initial={'title': content.title, 'body': content.body})
        except Content.DoesNotExist:
            content = None
            form = FormToUse()

    tvars = {'content': content,
             'form': form,
             'name': name}
    return render(request, 'wiki/edit.html', tvars)


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

    version1 = None
    version2 = None
    diff = None
    if request.GET and 'version1' in request.GET and 'version2' in request.GET:
        import difflib
        version1 = Content.objects.select_related().get(id=request.GET.get('version1'))
        version2 = Content.objects.select_related().get(id=request.GET.get('version2'))

        diff = difflib.HtmlDiff(4, 55).make_table(version1.body.split('\n'), version2.body.split('\n'), 'version %d' % version1.id, 'version %d' % version2.id, True, 5)

    tvars = {'page': page,
             'versions': versions,
             'version1': version1,
             'version2': version2,
             'diff': diff}
    return render(request, 'wiki/history.html', tvars)
