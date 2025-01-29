from django.urls import path
from . import views

urlpatterns = [
    path('',views.collections_for_user, name='collections'),
    path('<int:collection_id>/', views.collections_for_user, name='collections'),
    path('<int:collectionsound_id>/delete/', views.delete_sound_from_collection, name='delete-sound-from-collection'),
    path('<int:sound_id>/add/', views.add_sound_to_collection, name='add-sound-to-collection'),
    path('get_form_for_collection_sound/<int:sound_id>/', views.get_form_for_collecting_sound, name="collection-add-form-for-sound"),
    path('<int:collection_id>/edit', views.edit_collection, name="collection-edit"),
    path('<int:collection_id>/delete', views.delete_collection, name="delete-collection"),
    path('get_form_for_maintainer/<int:user_id>/', views.get_form_for_maintainer, name="add-maintainer-form"),
    path('<int:user_id>/add/', views.add_maintainer_to_collection, name="add-maintainer-to-collection")
]