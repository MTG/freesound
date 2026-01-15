from django.urls import path

from . import views

urlpatterns = [
    path("", views.collections_for_user, name="your-collections"),
    path("<str:collection_name>-<int:collection_id>/", views.collection, name="collection"),
    path("<int:sound_id>/add/", views.add_sound_to_collection, name="add-sound-to-collection"),
    path("create/", views.create_collection, name="create-collection"),
    path("<str:collection_name>-<int:collection_id>/edit", views.edit_collection, name="edit-collection"),
    path("<str:collection_name>-<int:collection_id>/delete", views.delete_collection, name="delete-collection"),
    path("<str:collection_name>-<int:collection_id>/download/", views.download_collection, name="download-collection"),
    path("<str:collection_name>-<int:collection_id>/licenses/", views.collection_licenses, name="collection-licenses"),
    path(
        "<str:collection_name>-<int:collection_id>/addsoundsmodal",
        views.add_sounds_modal_for_collection_edit,
        name="add-sounds-modal-collection",
    ),
    path("<str:collection_name>-<int:collection_id>/addmaintainersmodal", views.add_maintainer_modal, name="add-maintainers-modal"),
    path("<str:collection_name>-<int:collection_id>/section/stats", views.collection_stats_section, name="collection-stats-section"),
]
