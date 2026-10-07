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
import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from pytest_django.asserts import assertContains

from wiki.models import Content, Page


@pytest.fixture
def wiki_pages(load_fixtures):
    load_fixtures(["users"])
    blank = Page.objects.create(name="blank")
    user = User.objects.get(username="User1")
    Content.objects.create(page=blank, author=user, title="Blank page", body="This is a blank page")

    page = Page.objects.create(name="help")
    help2 = Content.objects.create(page=page, author=user, title="FS Help", body="Help version 2")
    help3 = Content.objects.create(page=page, author=user, title="FS Help", body="Help version 3")
    Page.objects.create(name="nocontent")
    return user, [help2.id, help3.id]


@pytest.fixture
def editable_wiki_page(load_fixtures):
    load_fixtures(["users"])
    admin = User.objects.get(username="User1")
    blank = Page.objects.create(name="blank")
    Content.objects.create(page=blank, author=admin, title="Blank page", body="This is a blank page")
    page = Page.objects.create(name="help")
    Content.objects.create(page=page, author=admin, title="FS Help", body="Help version 2")
    return page


class TestWiki:
    def test_page(self, wiki_pages, client):
        resp = client.get(reverse("wiki-page", kwargs={"name": "help"}))
        assertContains(resp, "Help version 3")

    def test_admin_page(self, wiki_pages, client):
        # An admin user has a link to edit the page
        user, _ = wiki_pages
        client.force_login(user)
        resp = client.get(reverse("wiki-page", kwargs={"name": "help"}))
        assertContains(resp, "Edit this page")

    def test_page_version(self, wiki_pages, client):
        _, help_ids = wiki_pages
        helpurl = reverse("wiki-page", kwargs={"name": "help"})
        # Old version of the page
        resp = client.get("%s?version=%d" % (helpurl, help_ids[0]))
        assertContains(resp, "Help version 2")

        # Version that doesn't exist (uses latest)
        resp = client.get(f"{helpurl}?version=100")
        assertContains(resp, "Help version 3")

        # Not a number in version param (uses latest)
        resp = client.get(f"{helpurl}?version=notint")
        assertContains(resp, "Help version 3")

    def test_page_with_no_content(self, wiki_pages, client):
        resp = client.get(reverse("wiki-page", kwargs={"name": "nocontent"}))
        assertContains(resp, "This is a blank page")

    def test_page_no_page(self, wiki_pages, client):
        resp = client.get(reverse("wiki-page", kwargs={"name": "nopage"}))
        assertContains(resp, "This is a blank page")


class TestEditWikiPage:
    def test_permissions(self, editable_wiki_page, client):
        admin = User.objects.get(username="User1")
        user3 = User.objects.get(username="User3")
        user4 = User.objects.get(username="User4")
        # User with no permissions get 404
        client.force_login(user3)
        resp = client.get(reverse("wiki-page-edit", kwargs={"name": "help"}))
        assert resp.status_code == 404

        # User with wiki edit permissions can edit
        wikict = ContentType.objects.get_for_model(Page)
        p = Permission.objects.get(content_type=wikict, codename="add_page")
        user4.user_permissions.add(p)
        client.force_login(user4)

        resp = client.get(reverse("wiki-page-edit", kwargs={"name": "help"}))
        assert resp.status_code == 200

        # Admin can edit
        client.force_login(admin)
        resp = client.get(reverse("wiki-page-edit", kwargs={"name": "help"}))
        assert resp.status_code == 200

    def test_edit_page_latest(self, editable_wiki_page, client):
        client.force_login(User.objects.get(username="User1"))
        resp = client.get(reverse("wiki-page-edit", kwargs={"name": "help"}))

        assertContains(resp, "FS Help")
        assertContains(resp, "Help version 2")
        # A page that exists has a link to a history page
        assertContains(resp, "history and comparison")

    def test_edit_page_no_page(self, editable_wiki_page, client):
        # If you edit a page that's not in the database it's not populated in the HTML
        client.force_login(User.objects.get(username="User1"))
        resp = client.get(reverse("wiki-page-edit", kwargs={"name": "notapage"}))

        assertContains(resp, 'placeholder="Contents of the page. You can use Markdown formatting and HTML."')
        assertContains(resp, 'placeholder="Title of the page"')

    def test_edit_page_save(self, editable_wiki_page, client):
        # POST to the form and a new Content for this page is created
        client.force_login(User.objects.get(username="User1"))
        resp = client.post(
            reverse("wiki-page-edit", kwargs={"name": "help"}),
            data={"title": "Page title", "body": "This is some body"},
        )
        content = editable_wiki_page.content()
        assert content.title == "Page title"
        assert content.body == "This is some body"
