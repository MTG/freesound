from django.urls import path

from . import views

urlpatterns = [
    path("", views.collections_for_user, name="your-collections"),
    path("<int:collection_id>-<slug:collection_name>/", views.collection, name="collection"),
    path("<int:sound_id>/add/", views.add_sound_to_collection, name="add-sound-to-collection"),
    path("create/", views.create_collection, name="create-collection"),
    path("<int:collection_id>-<slug:collection_name>/edit", views.edit_collection, name="edit-collection"),
    path("<int:collection_id>-<slug:collection_name>/delete", views.delete_collection, name="delete-collection"),
    path("<int:collection_id>-<slug:collection_name>/download/", views.download_collection, name="download-collection"),
    path("<int:collection_id>-<slug:collection_name>/licenses/", views.collection_licenses, name="collection-licenses"),
    path(
        "<int:collection_id>-<slug:collection_name>/addsoundsmodal",
        views.add_sounds_modal_for_collection_edit,
        name="add-sounds-modal-collection",
    ),
    path(
        "<int:collection_id>-<slug:collection_name>/addmaintainersmodal",
        views.add_maintainer_modal,
        name="add-maintainers-modal",
    ),
    path(
        "<int:collection_id>-<slug:collection_name>/section/stats",
        views.collection_stats_section,
        name="collection-stats-section",
    ),
]
