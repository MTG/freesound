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

from forms import ApiKeyForm
from models import ApiKey
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext

@login_required
def create_api_key(request):
    if request.method == 'POST':
        form = ApiKeyForm(request.POST)
        if form.is_valid():
            db_api_key = ApiKey()
            db_api_key.user = request.user
            db_api_key.description = form.cleaned_data['description']
            db_api_key.name        = form.cleaned_data['name']
            db_api_key.url         = form.cleaned_data['url']
            db_api_key.save()
            form = ApiKeyForm()
    else:
        form = ApiKeyForm()
    return render_to_response('api/apply_key.html', 
                              { 'user': request.user, 'form': form }, 
                              context_instance=RequestContext(request))