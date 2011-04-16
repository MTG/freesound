from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from general.models import OrderedModel
from django.db import transaction

@staff_member_required
@transaction.commit_on_success
def admin_move_ordered_model(request, direction, model_type_id, model_id):
    OrderedModel.move(direction, model_type_id, model_id)
    
    ModelClass = ContentType.objects.get(id=model_type_id).model_class()
    
    app_label = ModelClass._meta.app_label
    model_name = ModelClass.__name__.lower()

    url = "/admin/%s/%s/" % (app_label, model_name)
    
    return HttpResponseRedirect(url)