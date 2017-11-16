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
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from wiki.models import Content, Page


class WikiTestCase(TestCase):

    fixtures = ['users']

    def setUp(self):
        blank = Page.objects.create(name='blank')
        self.user = User.objects.get(username='User1')
        Content.objects.create(page=blank, author=self.user, title='Blank page', body='This is a blank page')

        page = Page.objects.create(name='help')
        help2 = Content.objects.create(page=page, author=self.user, title='FS Help', body='Help version 2')
        help3 = Content.objects.create(page=page, author=self.user, title='FS Help', body='Help version 3')
        self.help_ids = [help2.id, help3.id]

        Page.objects.create(name='nocontent')

    def test_page(self):
        resp = self.client.get(reverse('wiki-page', kwargs={'name': 'help'}))
        self.assertContains(resp, 'Help version 3')

    def test_admin_page(self):
        # An admin user has a link to edit the page
        self.client.force_login(self.user)
        resp = self.client.get(reverse('wiki-page', kwargs={'name': 'help'}))
        self.assertContains(resp, 'edit this page')

    def test_page_version(self):
        helpurl = reverse('wiki-page', kwargs={'name': 'help'})
        # Old version of the page
        resp = self.client.get('%s?version=%d' % (helpurl, self.help_ids[0]))
        self.assertContains(resp, 'Help version 2')

        # Version that doesn't exist (uses latest)
        resp = self.client.get('%s?version=100' % helpurl)
        self.assertContains(resp, 'Help version 3')

        # Not a number in version param (uses latest)
        resp = self.client.get('%s?version=notint' % helpurl)
        self.assertContains(resp, 'Help version 3')

    def test_page_with_no_content(self):
        resp = self.client.get(reverse('wiki-page', kwargs={'name': 'nocontent'}))
        self.assertContains(resp, 'This is a blank page')

    def test_page_no_page(self):
        resp = self.client.get(reverse('wiki-page', kwargs={'name': 'nopage'}))
        self.assertContains(resp, 'This is a blank page')


class EditWikiPageTest(TestCase):

    fixtures = ['users']

    def setUp(self):
        # User1 is an admin
        self.user1 = User.objects.get(username='User1')
        # Users 3 and 4 are non-admin, non-staff
        self.user3 = User.objects.get(username='User3')
        self.user4 = User.objects.get(username='User4')

        blank = Page.objects.create(name='blank')
        Content.objects.create(page=blank, author=self.user1, title='Blank page', body='This is a blank page')

        self.page = Page.objects.create(name='help')
        Content.objects.create(page=self.page, author=self.user1, title='FS Help', body='Help version 2')

    def test_permissions(self):
        # User with no permissions get 404
        self.client.force_login(self.user3)
        resp = self.client.get(reverse('wiki-page-edit', kwargs={'name': 'help'}))
        self.assertEqual(404, resp.status_code)

        # User with wiki edit permissions can edit
        wikict = ContentType.objects.get_for_model(Page)
        p = Permission.objects.get(content_type=wikict, codename='add_page')
        self.user4.user_permissions.add(p)
        self.client.force_login(self.user4)

        resp = self.client.get(reverse('wiki-page-edit', kwargs={'name': 'help'}))
        self.assertEqual(200, resp.status_code)

        # Admin can edit
        self.client.force_login(self.user1)
        resp = self.client.get(reverse('wiki-page-edit', kwargs={'name': 'help'}))
        self.assertEqual(200, resp.status_code)

    def test_edit_page_latest(self):
        self.client.force_login(self.user1)
        resp = self.client.get(reverse('wiki-page-edit', kwargs={'name': 'help'}))

        self.assertContains(resp, 'FS Help')
        self.assertContains(resp, 'Help version 2')
        # A page that exists has a link to a history page
        self.assertContains(resp, 'history and comparison')

    def test_edit_page_no_page(self):
        # If you edit a page that's not in the database it's not populated in the HTML
        self.client.force_login(self.user1)
        resp = self.client.get(reverse('wiki-page-edit', kwargs={'name': 'notapage'}))

        self.assertContains(resp, '<textarea name="body" id="id_body" rows="40" cols="100" required>\n</textarea>', html=True)
        self.assertContains(resp, '<input type="text" name="title" required id="id_title" size="100" />', html=True)

    def test_edit_page_save(self):
        # POST to the form and a new Content for this page is created
        self.client.force_login(self.user1)
        resp = self.client.post(reverse('wiki-page-edit', kwargs={'name': 'help'}), data={'title': 'Page title',
                                                                                          'body': 'This is some body'})
        content = self.page.content()
        self.assertEqual(content.title, 'Page title')
        self.assertEqual(content.body, 'This is some body')
