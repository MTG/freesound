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
from django.test import TestCase
from django.urls import reverse
from wiki.models import Page, Content
from django.conf import settings
from django.contrib.auth.models import User, Permission


class WikiPermissions(TestCase):

    def setUp(self):
        # Create wiki pages, one normal page and one for moderators
        self.normal_page = Page.objects.create(name="normal_page")
        self.normal_page_content = Content.objects.create(page=self.normal_page)
        self.moderators_page = Page.objects.create(name=settings.WIKI_MODERATORS_PAGE_CODENAME)
        self.moderators_page_content = Content.objects.create(page=self.moderators_page)

        # Create users
        self.normal_user = User.objects.create_user(username="normal_user", password="testpass")
        self.wiki_user = User.objects.create_user(username="wiki_user", password="testpass")
        self.wiki_user.user_permissions.add(Permission.objects.get(codename='add_page'))
        self.moderator_user = User.objects.create_user(username="moderator_user", password="testpass")
        self.moderator_user.user_permissions.add(Permission.objects.get(codename='can_moderate'))

    def test_view_wiki_page(self):

        # Non authenticated users can't visit moderation wiki pages, but can visit the others
        resp = self.client.get(reverse('wiki-page', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse('wiki-page', args=['normal_page']))
        self.assertEqual(resp.status_code, 200)

        # Logged in users can only visit moderation page if they are moderators or wiki editors
        self.client.login(username=self.normal_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.moderator_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 200)

        self.client.login(username=self.wiki_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 200)

        # Wiki pages other than moderators page can be visited by all logged in users
        self.client.login(username=self.normal_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page', args=['normal_page']))
        self.assertEqual(resp.status_code, 200)

        self.client.login(username=self.moderator_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page', args=['normal_page']))
        self.assertEqual(resp.status_code, 200)

        self.client.login(username=self.wiki_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page', args=['normal_page']))
        self.assertEqual(resp.status_code, 200)

    def test_edit_wiki_page(self):

        # Non authenticated users can't edit wiki pages
        resp = self.client.get(reverse('wiki-page-edit', args=['normal_page']))
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse('wiki-page-edit', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 404)

        # Normal wiki pages can only be edited by users with wiki edit perms
        self.client.login(username=self.normal_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-edit', args=['normal_page']))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.moderator_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-edit', args=['normal_page']))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.wiki_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-edit', args=['normal_page']))
        self.assertEqual(resp.status_code, 200)

        # Moderator page can be edited by users with wiki edit perms and moderators
        self.client.login(username=self.normal_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-edit', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.moderator_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-edit', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 200)

        self.client.login(username=self.wiki_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-edit', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 200)

    def test_history_wiki_page(self):
        # NOTE: History can be accessed by same users who can edit pages, therefore similar
        # tests as above apply:

        # Non authenticated users can't view history pages
        resp = self.client.get(reverse('wiki-page-history', args=['normal_page']))
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get(reverse('wiki-page-history', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 404)

        # Normal wiki history pages can only be viewed by users with wiki edit perms
        self.client.login(username=self.normal_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-history', args=['normal_page']))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.moderator_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-history', args=['normal_page']))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.wiki_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-history', args=['normal_page']))
        self.assertEqual(resp.status_code, 200)

        # Moderator page history can be viewed by users with wiki edit perms and moderators
        self.client.login(username=self.normal_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-history', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 404)

        self.client.login(username=self.moderator_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-history', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 200)

        self.client.login(username=self.wiki_user.username, password='testpass')
        resp = self.client.get(reverse('wiki-page-history', args=[settings.WIKI_MODERATORS_PAGE_CODENAME]))
        self.assertEqual(resp.status_code, 200)
