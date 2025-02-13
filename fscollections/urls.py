from django.urls import path
from . import views

urlpatterns = [
    path('',views.collections_for_user, name='collections'),
    path('<int:collection_id>/', views.collections_for_user, name='collections'),
    path('<int:collectionsound_id>/delete/', views.delete_sound_from_collection, name='delete-sound-from-collection'),
    path('<int:sound_id>/add/', views.add_sound_to_collection, name='add-sound-to-collection'),
    path('<int:sound_id>/get_form_for_collection_sound/', views.get_form_for_collecting_sound, name="collection-add-form-for-sound"),
    path('create/', views.create_collection, name='create-collection'),
    path('<int:collection_id>/edit', views.edit_collection, name="edit-collection"),
    path('<int:collection_id>/delete', views.delete_collection, name="delete-collection"),
    path('<int:collection_id>/addmaintainer', views.add_maintainer_to_collection, name="add-maintainers-to-collection"),
    path('<int:collection_id>/download/', views.download_collection, name="download-collection"),
    path('<int:collection_id>/licenses/', views.collection_licenses, name="collection-licenses")
]