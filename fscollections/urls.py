from django.urls import path
from . import views

urlpatterns = [
    path('',views.collections, name='collections'),
    path('<int:collection_id>/', views.collections, name='collections'),
    path('<int:collection_id>/<int:sound_id>/delete/', views.delete_sound_from_collection, name='delete-sound-from-collection'),
    path('<int:sound_id>/add/', views.add_sound_to_collection, name='add-sound-to-collection'),
    path('get_form_for_collection_sound/<int:sound_id>/', views.get_form_for_collecting_sound, name="collection-add-form-for-sound")
]