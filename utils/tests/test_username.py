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
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import DeletedUser, OldUsername
from utils.username import get_deleteduser_by_username, get_oldusername_by_username, get_user_by_username


@pytest.mark.django_db
def test_get_user_by_username():
    user = User.objects.create_user("MyUsername", password="pass")
    # exact
    assert get_user_by_username("MyUsername") == user
    # differing case
    assert get_user_by_username("myusername") == user
    assert get_user_by_username("MYUSERNAME") == user
    # Does not exist
    with pytest.raises(User.DoesNotExist):
        get_user_by_username("nonexistent")


@pytest.mark.django_db
def test_get_oldusername_by_username():
    user = User.objects.create_user("currentuser", password="pass")
    oldusername = OldUsername.objects.create(user=user, username="MyOldName")
    # exact
    assert get_oldusername_by_username("MyOldName") == oldusername
    # differing case
    assert get_oldusername_by_username("myoldname") == oldusername
    assert get_oldusername_by_username("MYOLDNAME") == oldusername
    with pytest.raises(OldUsername.DoesNotExist):
        get_oldusername_by_username("nonexistent")


@pytest.mark.django_db
def test_get_deleteduser_by_username():
    user = User.objects.create_user("originaluser", password="pass")
    deleted_user = DeletedUser.objects.create(
        user=user,
        username="MyDeletedName",
        email="deleted@example.com",
        date_joined=timezone.now(),
        reason=DeletedUser.DELETION_REASON_SELF_DELETED,
    )
    # exact
    assert get_deleteduser_by_username("MyDeletedName") == deleted_user
    # differing case
    assert get_deleteduser_by_username("mydeletedname") == deleted_user
    assert get_deleteduser_by_username("MYDELETEDNAME") == deleted_user
    with pytest.raises(DeletedUser.DoesNotExist):
        get_deleteduser_by_username("nonexistent")
