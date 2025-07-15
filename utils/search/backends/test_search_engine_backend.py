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

# Run tests in this file with:
#     pytest -m "search_engine"
# only sounds tests:
#     pytest -m "search_engine and sounds"
# only forum tests:
#     pytest -m "search_engine and forum"

import datetime
import json
import logging
import os
from unittest import mock
import time
from contextlib import contextmanager

from django.contrib.auth.models import User
import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone


from forum.models import Post, Forum, Thread
from search import solrapi
from sounds.models import Download, Sound
from tags.models import SoundTag
from utils.search import get_search_engine

console_logger = logging.getLogger("console")
console_logger.setLevel(logging.DEBUG)


def _setup_search_engine_backend(collection_type, schema_filename, unique_field, index_url_key, backend_class_name):
    """
    Helper function to set up a search engine backend for testing.

    Args:
        collection_type: Type of collection (e.g., "freesound", "forum")
        schema_filename: Name of the schema file to use
        unique_field: Unique field for the collection
        index_url_key: Key for the index URL in backend kwargs
        backend_class_name: Name of the backend class to use

    Returns:
        tuple: (backend, api_instance) where api_instance can be used for cleanup
    """
    if not settings.DEBUG:
        pytest.fail(
            "Running search engine tests in a production deployment. This should not be done as "
            "running these tests will modify the contents of the production search engine index "
            "and leave it in a 'wrong' state."
        )

    try:
        search_engine = get_search_engine(backend_class=backend_class_name)
    except ValueError:
        pytest.fail(
            "Wrong backend name format. Should be a path like "
            "utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine"
        )
    except ImportError as e:
        pytest.fail(f"Backend class to test could not be imported: {e}")

    today = datetime.datetime.now().strftime("%Y%m%d")
    temp_collection_name = f"engine_test_{collection_type}_{today}"

    api = solrapi.SolrManagementAPI(
        search_engine.solr_base_url, temp_collection_name
    )

    # Create new collection
    schema_directory = os.path.join(".", "utils", "search", "schema")
    schema_definition = json.load(
        open(os.path.join(schema_directory, schema_filename))
    )
    delete_default_fields_definition = json.load(
        open(os.path.join(schema_directory, "delete_default_fields.json"))
    )

    print(f"Creating collection {temp_collection_name} with schema {schema_filename}")
    api.create_collection_and_schema(
        delete_default_fields_definition, schema_definition, unique_field
    )

    index_url = f"{search_engine.solr_base_url}/solr/{temp_collection_name}"
    backend_kwargs = {"backend_class": backend_class_name, "sounds_index_url": None, "forum_index_url": None}
    backend_kwargs[index_url_key] = index_url
    backend = get_search_engine(**backend_kwargs)

    return backend, api


@pytest.fixture()
def search_engine_sounds_backend(request, test_sounds):
    backend_class_name = request.config.option.search_engine_backend
    backend, api = _setup_search_engine_backend(
        collection_type="freesound",
        schema_filename="freesound.json",
        unique_field="username",
        index_url_key="sounds_index_url",
        backend_class_name=backend_class_name,
    )

    backend.add_sounds_to_index(test_sounds)
    yield backend

    # Only delete if not keeping indexes
    if not request.config.option.keep_solr_index:
        if api.collection_exists():
            api.delete_collection()
    else:
        print(f"Keeping Solr index for inspection: {api.collection}")


@pytest.fixture()
def fake_analyzer_settings_for_similarity_tests(settings):
    settings.SEARCH_ENGINE_SIMILARITY_ANALYZERS = {
        "test_analyzer": {
            'vector_property_name': 'embeddings', 
            'vector_size': 100,}
        }
    settings.SEARCH_ENGINE_DEFAULT_SIMILARITY_ANALYZER = 'test_analyzer'


@pytest.fixture()
def search_engine_sounds_backend_for_similarity_tests(request, fake_analyzer_settings_for_similarity_tests, test_sounds):
    backend_class_name = request.config.option.search_engine_backend
    backend, api = _setup_search_engine_backend(
        collection_type="freesound",
        schema_filename="freesound.json",
        unique_field="username",
        index_url_key="sounds_index_url",
        backend_class_name=backend_class_name,
    )

    # Monkey patch add_similarity_vectors_to_documents to add fake similarity vectors which are consturcted based on the sound ID number
    def patched_add_similarity_vectors_to_documents(sound_objects, documents):
        for document in documents:
            document['similarity_vectors'] = [{
                    'content_type': 'v',  # Content type for similarity vectors
                    'analyzer': 'test_analyzer',
                    'timestamp_start': 0,
                    'timestamp_end': -1,
                    'sim_vector100': [document['id'] for _ in range(100)],  # Use fake vectors using sound ID so we can do some easy checks later
            }]
    backend.add_similarity_vectors_to_documents = patched_add_similarity_vectors_to_documents

    backend.add_sounds_to_index(test_sounds, include_similarity_vectors=True)
    yield backend

    # Only delete if not keeping indexes
    if not request.config.option.keep_solr_index:
        if api.collection_exists():
            api.delete_collection()
    else:
        print(f"Keeping Solr index for inspection: {api.collection}")


@pytest.fixture()
def search_engine_forum_backend(request, test_posts):
    backend_class_name = request.config.option.search_engine_backend
    backend, api = _setup_search_engine_backend(
        collection_type="forum",
        schema_filename="forum.json",
        unique_field="thread_id",
        index_url_key="forum_index_url",
        backend_class_name=backend_class_name,
    )

    backend.add_forum_posts_to_index(test_posts)
    yield backend

    # Only delete if not keeping indexes
    if not request.config.option.keep_solr_index:
        if api.collection_exists():
            api.delete_collection()
    else:
        print(f"Keeping Solr index for inspection: {api.collection}")


@pytest.fixture()
def test_sounds(db):
    call_command('loaddata', 'sounds/fixtures/licenses.json', 'sounds/fixtures/sounds_with_tags.json', verbosity=0)
    sound_ids = Sound.public.filter(
            is_index_dirty=False, num_ratings__gte=settings.MIN_NUMBER_RATINGS
        ).values_list('id', flat=True)
    sounds = list(Sound.objects.bulk_query_solr(sound_ids))
    if len(sound_ids) < 20:
        pytest.fail(
            f"Can't test search engine backend as there are not enough sounds for testing: {len(sounds)}, needed: 20"
        )
    return sounds


@pytest.fixture()
def test_users(db):
    call_command('loaddata', 'accounts/fixtures/users.json', verbosity=0)
    users = User.objects.all()
    return users


@pytest.fixture
def test_posts(test_users, db):
    forum_data = [
        ("General Discussion", "general-discussion", "General topics and discussions"),
        ("Sound Design", "sound-design", "Sound design techniques and tips"),
        ("Technical Support", "technical-support", "Technical questions and help"),
    ]

    forums = []
    for i, (name, slug, description) in enumerate(forum_data):
        forums.append(Forum(
            name=name,
            name_slug=slug,
            description=description,
            order=i
        ))

    Forum.objects.bulk_create(forums)
    for forum in forums:
        forum.refresh_from_db()

    threads = [
        Thread(
            forum=forums[0],
            author=test_users[1],
            title="Welcome to the community!",
            status=2
        ),
        Thread(
            forum=forums[1],
            author=test_users[2],
            title="Foley recording techniques"
        ),
        Thread(
            forum=forums[2],
            author=test_users[3],
            title="DAW compatibility issues"
        ),
        Thread(
            forum=forums[0],
            author=test_users[1],
            title="Best headphones for mixing?"
        ),
        Thread(
            forum=forums[0],
            author=test_users[2],
            title="Best field recording locations"
        ),
        Thread(
            forum=forums[2],
            author=test_users[4],
            title="Sound effect processing techniques"
        ),
    ]

    Thread.objects.bulk_create(threads)
    for thread in threads:
        thread.refresh_from_db()

    all_posts = []
    base_time = timezone.now() - timezone.timedelta(days=30)

    post_content = [
        "Welcome everyone! This is a great place to discuss audio and sound design.",
        "Thanks for the welcome! I'm excited to be here and learn from everyone.",
        "I agree, this community is really helpful for beginners like me.",
        "Does anyone have recommendations for good microphone equipment?",
        "Don't forget about room acoustics - that's often more important than the mic itself.",
    ]

    for i, content in enumerate(post_content):
        all_posts.append(Post(
            thread=threads[0],
            author=test_users[i % len(test_users)],
            body=content,
            moderation_state="OK",
            created=base_time + timezone.timedelta(hours=i*2)
        ))

    # Thread 2 posts
    foley_content = [
        "I'm working on a film project and need to record some foley sounds.",
        "What kind of sounds are you looking to record? Footsteps, impacts, or something else?",
        "Mostly footsteps on different surfaces - wood, concrete, grass, etc.",
        "For footsteps, try using different shoes and surfaces. A gravel path works great for crunching sounds.",
    ]

    for i, content in enumerate(foley_content):
        all_posts.append(Post(
            thread=threads[1],
            author=test_users[(i + 2) % len(test_users)],
            body=content,
            moderation_state="OK",
            created=base_time + timezone.timedelta(hours=24 + i*3)
        ))

    # Thread 3 posts
    tech_content = [
        "I'm having trouble with my DAW not recognizing my audio interface.",
        "What DAW and interface are you using? That will help diagnose the issue.",
        "I'm using Pro Tools with a Focusrite Scarlett 2i2.",
        "Have you tried updating your drivers? Focusrite has good driver support.",
    ]

    for i, content in enumerate(tech_content):
        all_posts.append(Post(
            thread=threads[2],
            author=test_users[(i + 1) % len(test_users)],
            body=content,
            moderation_state="OK",
            created=base_time + timezone.timedelta(hours=48 + i*2.5)
        ))

    # Thread 4 posts
    headphone_content = [
        "I need new headphones for mixing. Any recommendations?",
        "What's your budget? That will help narrow down the options.",
        "I'm looking to spend around $200-300.",
        "For that price range, I'd recommend the Audio-Technica ATH-M50x.",
    ]

    for i, content in enumerate(headphone_content):
        all_posts.append(Post(
            thread=threads[3],
            author=test_users[i % len(test_users)],
            body=content,
            moderation_state="OK",
            created=base_time + timezone.timedelta(hours=72 + i*1.8)
        ))

    # Thread 5 posts
    field_recording_content = [
        "I'm planning a field recording trip and looking for interesting locations.",
        "What kind of sounds are you looking to capture?",
        "I want to record natural ambiences and environmental sounds.",
        "Forests are great for bird sounds and wind through trees.",
        "Don't forget about urban environments - city ambiences are fascinating.",
    ]

    for i, content in enumerate(field_recording_content):
        all_posts.append(Post(
            thread=threads[4],
            author=test_users[(i + 1) % len(test_users)],
            body=content,
            moderation_state="OK",
            created=base_time + timezone.timedelta(hours=96 + i*2.2)
        ))

    # Thread 6 posts
    sound_effects_content = [
        "I'm working on a sound effect library and need processing advice.",
        "What type of sound effects are you creating?",
        "Mostly impact sounds and mechanical effects for games.",
        "What about pitch shifting? It can create great variations.",
        "I use pitch shifting a lot - it's great for creating monster sounds.",
    ]

    for i, content in enumerate(sound_effects_content):
        all_posts.append(Post(
            thread=threads[5],
            author=test_users[(i + 2) % len(test_users)],
            body=content,
            moderation_state="OK",
            created=base_time + timezone.timedelta(hours=120 + i*1.5)
        ))

    Post.objects.bulk_create(all_posts)
    for post in all_posts:
        post.refresh_from_db()

    for forum in forums:
        forum.set_last_post(commit=True)

    if len(all_posts) < 20:
        pytest.fail(
            f"Can't test search engine backend as there are not enough forum posts for testing: {len(all_posts)}, needed: 20"
        )

    return all_posts


@pytest.fixture(scope="session")
def output_file_handle(request):
    """Session-scoped fixture that provides a file handler for writing search backend test results, using the backend name from pytest options."""
    base_dir = os.path.join(settings.DATA_PATH, 'search_backend_tests')
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    date_label = timezone.now().strftime('%Y%m%d_%H%M')
    backend_name = request.config.option.search_engine_backend
    write_output = request.config.option.write_search_engine_output
    file_path = os.path.join(base_dir, f'{date_label}_test_results_{backend_name}.txt')
    if write_output:
        with open(file_path, 'w') as f:
            f.write(f'TESTING SEARCH ENGINE BACKEND: {backend_name}\n')
            yield f
    else:
        yield None


def write_search_results_to_file(f, results, query_params=None, query_type=None, elapsed_time=None):
    """
    Helper to append search results to the shared output file.
    Args:
        results: SearchResults object
        file_path: path to the output file (from fixture)
        query_params: dict of query parameters (optional)
        query_type: string label for the query type (optional)
        elapsed_time: float, seconds (optional)
    """
    if query_type or query_params or elapsed_time is not None:
        f.write(f'\n* QUERY {query_type or ""}: {str(query_params) if query_params else ""}')
        if elapsed_time is not None:
            f.write(f' (took {elapsed_time:.2f} seconds)')
        f.write('\n')
    f.write(
        f"num_found: {results.num_found}\n"
        f"non_grouped_number_of_results: {results.non_grouped_number_of_results}\n"
        f"q_time: {results.q_time}\n"
        f"facets: {results.facets}\n"
        f"highlighting: {results.highlighting}\n"
        f"docs:\n"
    )
    for count, doc in enumerate(results.docs):
        f.write(f"\t{count + 1}. {doc.get('id', '?')}: {doc}\n")


def run_sounds_query_and_save_results(search_engine_backend, output_file_handle, query_params):
        start = time.monotonic()
        results = search_engine_backend.search_sounds(**query_params)
        end = time.monotonic()
        if output_file_handle is not None:
            write_search_results_to_file(output_file_handle, results, query_params=query_params, elapsed_time=end - start, query_type="SOUNDS")
        return results


def run_forum_posts_query_and_save_results(search_engine_backend, output_file_handle, query_params):
        start = time.monotonic()
        results = search_engine_backend.search_forum_posts(**query_params)
        end = time.monotonic()
        if output_file_handle is not None:
            write_search_results_to_file(output_file_handle, results, query_params=query_params, elapsed_time=end - start, query_type="FORUM POSTS")
        return results


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_mandatory_doc_fields(search_engine_sounds_backend, output_file_handle):
    """Test that returned sounds include mandatory fields"""
    # Check non-grouped search results
    mandatory_fields = ["id", "score"]
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(num_sounds=1, group_by_pack=False))
    assert results.num_found > 0, "No results returned"
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when not grouping"
            )

    # Check grouped search results
    mandatory_fields = ["id", "score", "group_name", "n_more_in_group", "group_docs"]
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(
        num_sounds=1, group_by_pack=True, only_sounds_with_pack=True
    ))
    assert results.num_found > 0, "No results returned"
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when grouping by pack"
            )


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_random_sound(search_engine_sounds_backend):
    """Test random sound selection"""
    random_ids = []
    for _ in range(10):
        new_id = search_engine_sounds_backend.get_random_sound_id()
        random_ids.append(new_id)

    assert len(random_ids) == 10, "Didn't get enough random sound IDs"
    # Because we have few sounds in the test database, we might sometimes get repeated IDs
    # Check that we have "enough" ids, might not always be 10 different ones
    assert len(set(random_ids)) >= 7, "Got more repeated sound IDs in subsequent calls to 'get random sound id' than expected"


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_offsets(search_engine_sounds_backend, output_file_handle):
    """Test pagination and offset functionality"""
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(num_sounds=10, offset=0))
    offset_0_ids = [r["id"] for r in results.docs]
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(num_sounds=10, offset=1))
    offset_1_ids = [r["id"] for r in results.docs]

    assert len(offset_0_ids) == 10
    assert len(offset_1_ids) == 10
    assert offset_0_ids[1:] == offset_1_ids[:-1]

    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(num_sounds=1, offset=4))
    offset_4_num_sounds_1_ids = [r["id"] for r in results.docs]
    assert len(offset_4_num_sounds_1_ids) == 1
    assert offset_0_ids[4] == offset_4_num_sounds_1_ids[0]

    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(num_sounds=5, current_page=2))
    page_2_num_sounds_5_ids = [r["id"] for r in results.docs]
    assert len(page_2_num_sounds_5_ids) == 5
    assert page_2_num_sounds_5_ids == offset_0_ids[5:]


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_empty_query(search_engine_sounds_backend, output_file_handle):
    """Test empty query returns results"""
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=""))
    assert results.num_found > 0, "Empty query returned no results"


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_sort_parameter(search_engine_sounds_backend, output_file_handle, test_sounds):
    """Test sorting functionality"""
    for sort_option_web in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB:
        results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(
            sort=sort_option_web,
            num_sounds=len(test_sounds),
            only_sounds_within_ids=[s.id for s in test_sounds],
        ))
        result_ids = [r["id"] for r in results.docs]
        sounds = Sound.objects.ordered_ids(result_ids)
        assert sorted([s.id for s in test_sounds]) == sorted(result_ids), (
            "only_sounds_within_ids not respected"
        )

        # Assert sorting criteria is preserved
        for sound1, sound2 in zip(sounds[:-1], sounds[1:]):
            if sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC:
                pass  # Nothing to test here as there's no expected result
            elif (
                sort_option_web
                == settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST
            ):
                assert (
                    Download.objects.filter(sound=sound1).count()
                    >= Download.objects.filter(sound=sound2).count()
                )
            elif (
                sort_option_web
                == settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_LEAST_FIRST
            ):
                assert (
                    Download.objects.filter(sound=sound1).count()
                    <= Download.objects.filter(sound=sound2).count()
                )
            elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DATE_OLD_FIRST:
                assert sound1.created <= sound2.created
            elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST:
                assert sound1.created >= sound2.created
            elif (
                sort_option_web
                == settings.SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST
            ):
                assert sound1.avg_rating <= sound2.avg_rating
                if sound1.avg_rating == sound2.avg_rating:
                    assert sound1.num_ratings >= sound2.num_ratings
            elif (
                sort_option_web
                == settings.SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST
            ):
                assert sound1.avg_rating >= sound2.avg_rating
                if sound1.avg_rating == sound2.avg_rating:
                    assert sound1.num_ratings >= sound2.num_ratings
            elif (
                sort_option_web
                == settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST
            ):
                assert sound1.duration >= sound2.duration
            elif (
                sort_option_web
                == settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST
            ):
                assert sound1.duration <= sound2.duration


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_group_by_pack(search_engine_sounds_backend, output_file_handle):
    """Test grouping by pack functionality"""
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(group_by_pack=True))
    for result in results.docs:
        assert "id" in result, "No ID field in doc from results"
        assert "group_name" in result, "No group_name field in doc from results"
        assert "group_docs" in result, "No group_docs field in doc from results"
        assert "n_more_in_group" in result, (
            "No n_more_in_group field in doc from results"
        )
        group_sounds = Sound.objects.bulk_query_id(
            sound_ids=[int(r["id"]) for r in result["group_docs"]]
        )
        first_sound_pack = group_sounds[0].pack
        for sound in group_sounds:
            assert sound.pack == first_sound_pack, "Different packs in pack group"


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_sounds_with_pack(search_engine_sounds_backend, output_file_handle):
    """Test filtering sounds with pack"""
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(
        only_sounds_with_pack=True, num_sounds=50
    ))
    sounds = Sound.objects.bulk_query_id(sound_ids=[r["id"] for r in results.docs])
    for sound in sounds:
        assert sound.pack is not None, (
            'Sound without pack when using "only_sounds_with_pack"'
        )


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_facets(search_engine_sounds_backend, output_file_handle):
    """Test faceting functionality"""
    test_facet_options = {
        settings.SEARCH_SOUNDS_FIELD_USER_NAME: {"limit": 3},
        settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: {"limit": 1},
        settings.SEARCH_SOUNDS_FIELD_TYPE: {},
    }
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(facets=test_facet_options))
    assert len(results.facets) == 3, "Wrong number of facets returned"
    for facet_field, facet_options in test_facet_options.items():
        assert facet_field in results.facets, f"Facet {facet_field} not found in facets"
        if "limit" in facet_options:
            assert len(results.facets[facet_field]) == facet_options["limit"], (
                f"Wrong number of items in facet {facet_field}"
            )

    # Test if no facets requested, no facets returned
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict())
    assert results.facets == dict(), "Facets returned but not requested"


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_search_query_fields_parameter(search_engine_sounds_backend, output_file_handle, test_sounds):
    """Test that query_fields parameter works as expected matching only in the specified fields.
    This is used for the advanced search "SEARCH IN" functionality."""
    
    # Test that searching using the ID field only, returns exact match by ID
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=f"{test_sounds[0].id}", query_fields={settings.SEARCH_SOUNDS_FIELD_ID: 1}))
    assert results.docs[0]["id"] == test_sounds[0].id, (
        "Searching in the ID field did not return the expected sound"
    )

    # Test searching with a filename but only matching on ID does not return any results
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=f"{test_sounds[0].original_filename}", query_fields={settings.SEARCH_SOUNDS_FIELD_ID: 1}))
    assert results.num_found == 0, (
        "Searching in the 'ID' field did not return the expected number of results"
    )

    # Test matching on the original_filename field only
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=f"{test_sounds[0].original_filename}", query_fields={settings.SEARCH_SOUNDS_FIELD_NAME: 1}))
    assert results.docs[0]["id"] == test_sounds[0].id, (
        "Searching in the 'name' field did not return the expected sound"
    )

    # Test partial matching in the original_filename also works
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query="Glass E1", query_fields={settings.SEARCH_SOUNDS_FIELD_NAME: 1}))
    assert results.docs[0]["id"] == test_sounds[0].id, (
        "Searching in the 'name' field (partial match) did not return the expected sound"
    )

    # Test searching in the tags field...
    sound_with_tags = [s for s in test_sounds if s.get_sound_tags()][0]
    sound_tags = sound_with_tags.get_sound_tags()
    
    # ...first with all tags
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=" ".join(sound_tags), query_fields={settings.SEARCH_SOUNDS_FIELD_TAGS: 1}))
    result_sids = [s["id"] for s in results.docs]
    assert sound_with_tags.id in result_sids, (
        "Searching in the 'tags' field did not return the expected sound"
    )

    # ...then with only one of the tags
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=sound_tags[0], query_fields={settings.SEARCH_SOUNDS_FIELD_TAGS: 1}))
    result_sids = [s["id"] for s in results.docs]
    assert sound_with_tags.id in result_sids, (
        "Searching in the 'tags' field did not return the expected sound"
    )

    # Test searching in the description field...
    # ...first with full description
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=test_sounds[0].description, query_fields={settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 1}))
    assert results.docs[0]["id"] == test_sounds[0].id, (
        "Searching in the 'description' field did not return the expected sound"
    )

    # ...then with a partial description
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=" ".join(test_sounds[0].description.split(" ")[0:5]), query_fields={settings.SEARCH_SOUNDS_FIELD_DESCRIPTION: 1}))
    assert results.docs[0]["id"] == test_sounds[0].id, (
        "Searching in the 'description' field (partial match) did not return the expected sound"
    )

    # Test searching in the username field...
    username = "Twisted.Lemon"  # Known to be in the fixture data
    # ...first with full username
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=username, query_fields={settings.SEARCH_SOUNDS_FIELD_USER_NAME: 1}))
    results_first_sound = Sound.objects.get(id=results.docs[0]["id"])
    assert results_first_sound.user.username == username, (
        "Searching in the 'username' field did not return the expected sound"
    )

    # ...then with a partial username (note that the tokenizer splits on spaces and other punctuaiton symbols)
    partial_username = "Twisted"  # Partial username to test
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=partial_username, query_fields={settings.SEARCH_SOUNDS_FIELD_USER_NAME: 1}))
    results_first_sound = Sound.objects.get(id=results.docs[0]["id"])
    assert results_first_sound.user.username == username, (
        "Searching in the 'username' field (partial match) did not return the expected sound"
    )

    # Test searching in the pack name field...
    pack_name = "sinusoid pack"  # Known to be in the fixture data
    # ...first with full username
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=pack_name, query_fields={settings.SEARCH_SOUNDS_FIELD_PACK_NAME: 1}))
    results_first_sound = Sound.objects.get(id=results.docs[0]["id"])
    assert results_first_sound.pack.name == pack_name, (
        "Searching in the 'pack name' field did not return the expected sound"
    )

    # ...then with a partial pack name
    partial_pack_name = "sinusoid"  # Partial pack name to test
    results = run_sounds_query_and_save_results(search_engine_sounds_backend, output_file_handle, dict(textual_query=partial_pack_name, query_fields={settings.SEARCH_SOUNDS_FIELD_PACK_NAME: 1}))
    results_first_sound = Sound.objects.get(id=results.docs[0]["id"])
    assert results_first_sound.pack.name == username, (
        "Searching in the 'pack name' field (partial match) did not return the expected sound"
    )


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_user_tags(search_engine_sounds_backend, output_file_handle, test_sounds):
    """Test user tags functionality"""
    sound = test_sounds[0]
    user_tagged_items = (
        SoundTag.objects.filter(user=sound.user).select_related("tag").all()
    )
    all_user_tags = [ti.tag.name for ti in user_tagged_items]
    tags_and_counts = search_engine_sounds_backend.get_user_tags(sound.user.username)
    search_engine_tags = [t[0] for t in tags_and_counts]

    remaining_tags = set(search_engine_tags) - set(all_user_tags)
    assert len(remaining_tags) == 0, (
        "get_user_tags returned tags which the user hasn't tagged"
    )
    
    if output_file_handle is not None:
        output_file_handle.write(f'\n* USER "{sound.user.username}" TOP TAGS FROM SEARCH ENGINE: {search_engine_tags}\n')


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
def test_sound_pack_tags(search_engine_sounds_backend, output_file_handle, test_sounds):
    """Test pack tags functionality"""
    # Find a sound in our dataset of known sounds that has a pack and tags
    target_sound = None
    for sound in test_sounds:
        if sound.pack and sound.tags.count():
            target_sound = sound
            break

    assert target_sound is not None, (
        "Sample sounds dataset doesn't have any sounds with a pack and tags"
    )

    pack = target_sound.pack
    all_sound_tags = []
    for s in pack.sounds.all():
        all_sound_tags.extend([t.lower() for t in s.get_sound_tags()])

    tags_and_counts = search_engine_sounds_backend.get_pack_tags(
        target_sound.user.username, pack.name
    )
    search_engine_tags = [t[0].lower() for t in tags_and_counts]
    remaining_tags = set(search_engine_tags) - set(all_sound_tags)
    assert len(remaining_tags) == 0, (
        "get_pack_tags returned tags which the user hasn't tagged"
    )

    if output_file_handle is not None:
        output_file_handle.write(f'\n* PACK "{pack.id}" TOP TAGS FROM SEARCH ENGINE: {search_engine_tags}\n')


@pytest.mark.search_engine
@pytest.mark.sounds
@pytest.mark.django_db
@mock.patch("utils.search.backends.solr555pysolr.get_similarity_search_target_vector")
def test_sound_similarity_search(
    get_similarity_search_target_vector, search_engine_sounds_backend_for_similarity_tests, output_file_handle, test_sounds
):
    """Test similarity search functionality"""

    # Make sure sounds are sorted by ID so that in similarity search the closest sound is either the next or the previous one
    test_sounds = sorted(test_sounds, key=lambda x: x.id)

    # Implement mock for get_similarity_search_target_vector to return a vector based on the sound ID number
    get_similarity_search_target_vector.return_value = [
        test_sounds[0].id for _ in range(100)  # Will return vector corresponding to the first sound ID, with ID 6
    ]

    # Make a query for target sound 0 and check that results are sorted by ID
    results = run_sounds_query_and_save_results(search_engine_sounds_backend_for_similarity_tests, output_file_handle, dict(
        similar_to=test_sounds[0].id,
        similar_to_max_num_sounds=10,
        similar_to_analyzer="test_analyzer",
    ))
    results_ids = [r["id"] for r in results.docs]
    sounds_ids = [s.id for s in test_sounds][
        1:11
    ]  # target sound is expected to be in results
    assert results_ids == sounds_ids, (
        "Similarity search did not return sounds sorted as expected when searching with a target sound ID"
    )

    # Now make the same query but passing an arbitrary vector
    target_sound_vector = [test_sounds[0].id for _ in range(100)]
    results = run_sounds_query_and_save_results(search_engine_sounds_backend_for_similarity_tests, output_file_handle, dict(
        similar_to=target_sound_vector,
        similar_to_max_num_sounds=10,
        similar_to_analyzer="test_analyzer",
    ))
    results_ids = [r["id"] for r in results.docs]
    sounds_ids = [s.id for s in test_sounds][
        0:10
    ]  # target sound is expected to be in results
    assert results_ids == sounds_ids, (
        "Similarity search did not return sounds sorted as expected when searching with a target vector"
    )

    # Check requesting sounds for an analyzer that doesn't exist
    results = run_sounds_query_and_save_results(search_engine_sounds_backend_for_similarity_tests, output_file_handle, dict(
        similar_to=target_sound_vector,
        similar_to_max_num_sounds=10,
        similar_to_analyzer="test_analyzer2",
    ))
    assert len(results.docs) == 0, (
        "Similarity search returned results for an analyzer that doesn't exist"
    )

    # Check similar_to_max_num_sounds parameter
    results = run_sounds_query_and_save_results(search_engine_sounds_backend_for_similarity_tests, output_file_handle, dict(
        similar_to=target_sound_vector,
        similar_to_max_num_sounds=5,
        similar_to_analyzer="test_analyzer",
    ))
    assert len(results.docs) == 5, (
        "Similarity search returned unexpected number of results"
    )


@pytest.mark.search_engine
@pytest.mark.forum
@pytest.mark.django_db
def test_forum_mandatory_doc_fields(search_engine_forum_backend, output_file_handle):
    """Test that returned forum posts include mandatory fields"""
    # Check non-grouped search results
    mandatory_fields = [
        "id",
        "score",
        "post_body",
        "thread_author",
        "forum_name",
        "forum_name_slug",
    ]
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(
        num_posts=1, group_by_thread=False)
    )
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when not grouping by thread"
            )

    # Check grouped search results
    mandatory_fields = ["id", "score", "group_name", "n_more_in_group", "group_docs"]
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(
        num_posts=1, group_by_thread=True
    ))
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when grouping by thread"
            )


@pytest.mark.search_engine
@pytest.mark.forum
@pytest.mark.django_db
def test_forum_offsets(search_engine_forum_backend, output_file_handle):
    """Test forum post pagination and offset functionality"""

    # This groups by thread. We only have 6 test threads, so limit to 5
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(num_posts=5, offset=0))
    offset_0_ids = [r["id"] for r in results.docs]
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(num_posts=5, offset=1))
    offset_1_ids = [r["id"] for r in results.docs]

    assert len(offset_0_ids) == 5
    assert len(offset_1_ids) == 5
    assert offset_0_ids[1:] == offset_1_ids[:-1]

    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(num_posts=1, offset=3))
    offset_4_num_posts_1_ids = [r["id"] for r in results.docs]
    assert len(offset_4_num_posts_1_ids) == 1
    assert offset_0_ids[3] == offset_4_num_posts_1_ids[0]

    # With 6 threads, we should get 1 result on page 2 if we show 5 posts per page
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(num_posts=5, current_page=2))
    page_2_num_posts_5_ids = [r["id"] for r in results.docs]
    assert len(page_2_num_posts_5_ids) == 1
    assert page_2_num_posts_5_ids == offset_1_ids[-1:]

    # Test that results are sorted by newest posts first
    expected_fields = [
        "id",
        "forum_name",
        "forum_name_slug",
        "thread_id",
        "thread_title",
        "thread_author",
        "thread_created",
        "post_body",
        "post_author",
        "post_created",
        "num_posts",
    ]
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(group_by_thread=False))
    for result1, result2 in zip(results.docs[:-1], results.docs[1:]):
        for field in expected_fields:
            assert field in result1, f"{field} not present in result ID {result1['id']}"
        assert result1["thread_created"] >= result2["thread_created"], (
            "Wrong sorting in query results"
        )


@pytest.mark.search_engine
@pytest.mark.forum
@pytest.mark.django_db
def test_forum_empty_query(search_engine_forum_backend, output_file_handle):
    """Test empty forum query returns results"""
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(textual_query=""))
    assert results.num_found > 0, "Empty query returned no results"


@pytest.mark.search_engine
@pytest.mark.forum
@pytest.mark.django_db
def test_forum_group_by_thread(search_engine_forum_backend, output_file_handle):
    """Test forum post grouping by thread"""
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict())
    for result in results.docs:
        assert "id" in result, "No ID field in doc from results"
        assert "group_name" in result, "No group_name field in doc from results"
        assert "group_docs" in result, "No group_docs field in doc from results"
        assert "n_more_in_group" in result, (
            "No n_more_in_group field in doc from results"
        )

        first_post_thread = result["group_docs"][0]["thread_title"]
        for doc in result["group_docs"]:
            assert doc["thread_title"] == first_post_thread, (
                "Different threads in thread group"
            )


@pytest.mark.search_engine
@pytest.mark.forum
@pytest.mark.django_db
def test_forum_highlighting(search_engine_forum_backend, output_file_handle):
    """Test forum post highlighting"""
    results = run_forum_posts_query_and_save_results(search_engine_forum_backend, output_file_handle, dict(textual_query="microphone"))
    assert results.highlighting != dict(), "No highlighting entries returned"
    for highlighting_content in results.highlighting.values():
        assert "post_body" in highlighting_content, (
            "Highlighting data without expected fields"
        )

