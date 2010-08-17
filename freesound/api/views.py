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
    else:
        form = ApiKeyForm()
    return render_to_response('api/apply_key.html', 
                              { 'user': request.user, 'form': form }, 
                              context_instance=RequestContext(request))