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

import pytest
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from forum.models import Post
from search import solrapi
from sounds.models import Download, Sound
from tags.models import SoundTag
from utils.search import get_search_engine

console_logger = logging.getLogger("console")
console_logger.setLevel(logging.DEBUG)


def _make_search_engine_backend_fixture(collection_type, schema_filename, unique_field, index_url_key):
    def _fixture(request):
        if not settings.DEBUG:
            pytest.fail(
                "Running search engine tests in a production deployment. This should not be done as "
                "running these tests will modify the contents of the production search engine index "
                "and leave it in a 'wrong' state."
            )

        backend_class_name = request.config.option.search_engine_backend
        if backend_class_name is None:
            pytest.fail(
                "No search engine backend class name provided. Please use the --search-engine-backend option to specify the backend class name."
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

        yield backend

        # Cleanup after tests
        if api.collection_exists():
            api.delete_collection()
    return _fixture


@pytest.fixture()
def search_engine_sounds_backend(request, test_sounds):
    # because the helper function returns a generator, we need to use next() manually to get the backend
    # before we can use it.
    gen = _make_search_engine_backend_fixture(
        collection_type="freesound",
        schema_filename="freesound.json",
        unique_field="username",
        index_url_key="sounds_index_url",
    )(request)
    backend = next(gen)
    backend.add_sounds_to_index(test_sounds)
    yield backend
    try:
        next(gen)
    except StopIteration:
        pass


@pytest.fixture()
def search_engine_forum_backend(request, test_posts):
    gen = _make_search_engine_backend_fixture(
        collection_type="forum",
        schema_filename="forum.json",
        unique_field="thread_id",
        index_url_key="forum_index_url",
    )(request)
    backend = next(gen)
    backend.add_forum_posts_to_index(test_posts)
    yield backend
    try:
        next(gen)
    except StopIteration:
        pass


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


@pytest.fixture
def test_posts():
    """Fixture to provide test forum posts"""
    posts = list(
        Post.objects.filter(moderation_state="OK")[0:20]
    )
    if len(posts) < 20:
        pytest.fail(
            f"Can't test search engine backend as there are not enough forum posts for testing: {len(posts)}, needed: 20"
        )
    return posts


@pytest.fixture(scope="session")
def search_backend_output_file_path(request):
    """Session-scoped fixture that provides a file path for writing search backend test results, using the backend name from pytest options."""
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
        yield file_path
    else:
        yield None


def write_search_results_to_file(results, file_path, query_data=None, query_type=None, elapsed_time=None):
    """
    Helper to append search results to the shared output file.
    Args:
        results: SearchResults object
        file_path: path to the output file (from fixture)
        query_data: dict of query parameters (optional)
        query_type: string label for the query type (optional)
        elapsed_time: float, seconds (optional)
    """
    if file_path is None:
        return
    with open(file_path, 'a') as f:
        if query_type or query_data or elapsed_time is not None:
            f.write(f'\n* QUERY {query_type or ""}: {str(query_data) if query_data else ""}')
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


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_mandatory_doc_fields(search_engine_sounds_backend):
    """Test that returned sounds include mandatory fields"""
    # Check non-grouped search results
    mandatory_fields = ["id", "score"]
    results = search_engine_sounds_backend.search_sounds(num_sounds=1, group_by_pack=False)
    assert results.num_found > 0, "No results returned"
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when not grouping"
            )

    # Check grouped search results
    mandatory_fields = ["id", "score", "group_name", "n_more_in_group", "group_docs"]
    results = search_engine_sounds_backend.search_sounds(
        num_sounds=1, group_by_pack=True, only_sounds_with_pack=True
    )
    assert results.num_found > 0, "No results returned"
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when grouping by pack"
            )


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_random_sound(search_engine_sounds_backend):
    """Test random sound selection"""
    last_id = 0
    for _ in range(10):
        new_id = search_engine_sounds_backend.get_random_sound_id()
        assert new_id != last_id, (
            'Repeated sound IDs in subsequent calls to "get random sound id" method'
        )
        last_id = new_id


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_offsets(search_engine_sounds_backend):
    """Test pagination and offset functionality"""
    results = search_engine_sounds_backend.search_sounds(num_sounds=10, offset=0)
    offset_0_ids = [r["id"] for r in results.docs]
    results = search_engine_sounds_backend.search_sounds(num_sounds=10, offset=1)
    offset_1_ids = [r["id"] for r in results.docs]

    assert len(offset_0_ids) == 10
    assert len(offset_1_ids) == 10
    assert offset_0_ids[1:] == offset_1_ids[:-1]

    results = search_engine_sounds_backend.search_sounds(num_sounds=1, offset=4)
    offset_4_num_sounds_1_ids = [r["id"] for r in results.docs]
    assert len(offset_4_num_sounds_1_ids) == 1
    assert offset_0_ids[4] == offset_4_num_sounds_1_ids[0]

    results = search_engine_sounds_backend.search_sounds(num_sounds=5, current_page=2)
    page_2_num_sounds_5_ids = [r["id"] for r in results.docs]
    assert len(page_2_num_sounds_5_ids) == 5
    assert page_2_num_sounds_5_ids == offset_0_ids[5:]


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_empty_query(search_engine_sounds_backend):
    """Test empty query returns results"""
    results = search_engine_sounds_backend.search_sounds(textual_query="")
    assert results.num_found > 0, "Empty query returned no results"


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_sort_parameter(search_engine_sounds_backend, test_sounds):
    """Test sorting functionality"""
    for sort_option_web in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB:
        results = search_engine_sounds_backend.search_sounds(
            sort=sort_option_web,
            num_sounds=len(test_sounds),
            only_sounds_within_ids=[s.id for s in test_sounds],
        )
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
@pytest.mark.django_db
def test_sound_group_by_pack(search_engine_sounds_backend):
    """Test grouping by pack functionality"""
    results = search_engine_sounds_backend.search_sounds(group_by_pack=True)
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
@pytest.mark.django_db
def test_sound_sounds_with_pack(search_engine_sounds_backend):
    """Test filtering sounds with pack"""
    results = search_engine_sounds_backend.search_sounds(
        only_sounds_with_pack=True, num_sounds=50
    )
    sounds = Sound.objects.bulk_query_id(sound_ids=[r["id"] for r in results.docs])
    for sound in sounds:
        assert sound.pack is not None, (
            'Sound without pack when using "only_sounds_with_pack"'
        )


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_facets(search_engine_sounds_backend):
    """Test faceting functionality"""
    test_facet_options = {
        settings.SEARCH_SOUNDS_FIELD_USER_NAME: {"limit": 3},
        settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: {"limit": 1},
        settings.SEARCH_SOUNDS_FIELD_TYPE: {},
    }
    results = search_engine_sounds_backend.search_sounds(facets=test_facet_options)
    assert len(results.facets) == 3, "Wrong number of facets returned"
    for facet_field, facet_options in test_facet_options.items():
        assert facet_field in results.facets, f"Facet {facet_field} not found in facets"
        if "limit" in facet_options:
            assert len(results.facets[facet_field]) == facet_options["limit"], (
                f"Wrong number of items in facet {facet_field}"
            )

    # Test if no facets requested, no facets returned
    results = search_engine_sounds_backend.search_sounds()
    assert results.facets == dict(), "Facets returned but not requested"


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_user_tags(search_engine_sounds_backend, test_sounds):
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


@pytest.mark.search_engine
@pytest.mark.django_db
def test_sound_pack_tags(search_engine_sounds_backend, test_sounds):
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


@pytest.mark.search_engine
@pytest.mark.django_db
@mock.patch("utils.search.backends.solr555pysolr.get_similarity_search_target_vector")
def test_sound_similarity_search(
    get_similarity_search_target_vector, search_engine_sounds_backend, test_sounds
):
    """Test similarity search functionality"""
    get_similarity_search_target_vector.return_value = [
        test_sounds[0].id for _ in range(100)
    ]
    # Make sure sounds are sorted by ID so that in similarity search the closest sound is either the next or the previous one
    test_sounds = sorted(test_sounds, key=lambda x: x.id)

    # Make a query for target sound 0 and check that results are sorted by ID
    results = search_engine_sounds_backend.search_sounds(
        similar_to=test_sounds[0].id,
        similar_to_max_num_sounds=10,
        similar_to_analyzer="test_analyzer",
    )
    results_ids = [r["id"] for r in results.docs]
    sounds_ids = [s.id for s in test_sounds][
        1:11
    ]  # target sound is not expected to be in results
    assert results_ids == sounds_ids, (
        "Similarity search did not return sounds sorted as expected when searching with a target sound ID"
    )

    # Now make the same query but passing an arbitrary vector
    target_sound_vector = [test_sounds[0].id for _ in range(100)]
    results = search_engine_sounds_backend.search_sounds(
        similar_to=target_sound_vector,
        similar_to_max_num_sounds=10,
        similar_to_analyzer="test_analyzer",
    )
    results_ids = [r["id"] for r in results.docs]
    sounds_ids = [s.id for s in test_sounds][
        0:10
    ]  # target sound is expected to be in results
    assert results_ids == sounds_ids, (
        "Similarity search did not return sounds sorted as expected when searching with a target vector"
    )

    # Check requesting sounds for an analyzer that doesn't exist
    results = search_engine_sounds_backend.search_sounds(
        similar_to=target_sound_vector,
        similar_to_max_num_sounds=10,
        similar_to_analyzer="test_analyzer2",
    )
    assert len(results.docs) == 0, (
        "Similarity search returned results for an analyzer that doesn't exist"
    )

    # Check similar_to_max_num_sounds parameter
    results = search_engine_sounds_backend.search_sounds(
        similar_to=target_sound_vector,
        similar_to_max_num_sounds=5,
        similar_to_analyzer="test_analyzer",
    )
    assert len(results.docs) == 5, (
        "Similarity search returned unexpected number of results"
    )


@pytest.mark.search_engine
@pytest.mark.django_db
def test_forum_mandatory_doc_fields(search_engine_forum_backend):
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
    results = search_engine_forum_backend.search_forum_posts(
        num_posts=1, group_by_thread=False
    )
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when not grouping by thread"
            )

    # Check grouped search results
    mandatory_fields = ["id", "score", "group_name", "n_more_in_group", "group_docs"]
    results = search_engine_forum_backend.search_forum_posts(
        num_posts=1, group_by_thread=True
    )
    for result in results.docs:
        for field in mandatory_fields:
            assert field in result, (
                f"Mandatory field {field} not present in result when grouping by thread"
            )


@pytest.mark.search_engine
@pytest.mark.django_db
def test_forum_offsets(search_engine_forum_backend):
    """Test forum post pagination and offset functionality"""
    results = search_engine_forum_backend.search_forum_posts(num_posts=10, offset=0)
    offset_0_ids = [r["id"] for r in results.docs]
    results = search_engine_forum_backend.search_forum_posts(num_posts=10, offset=1)
    offset_1_ids = [r["id"] for r in results.docs]

    assert len(offset_0_ids) == 10
    assert len(offset_1_ids) == 10
    assert offset_0_ids[1:] == offset_1_ids[:-1]

    results = search_engine_forum_backend.search_forum_posts(num_posts=1, offset=4)
    offset_4_num_posts_1_ids = [r["id"] for r in results.docs]
    assert len(offset_4_num_posts_1_ids) == 1
    assert offset_0_ids[4] == offset_4_num_posts_1_ids[0]

    results = search_engine_forum_backend.search_forum_posts(num_posts=5, current_page=2)
    page_2_num_posts_5_ids = [r["id"] for r in results.docs]
    assert len(page_2_num_posts_5_ids) == 5
    assert page_2_num_posts_5_ids == offset_0_ids[5:]

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
    results = search_engine_forum_backend.search_forum_posts(group_by_thread=False)
    for result1, result2 in zip(results.docs[:-1], results.docs[1:]):
        for field in expected_fields:
            assert field in result1, f"{field} not present in result ID {result1['id']}"
        assert result1["thread_created"] >= result2["thread_created"], (
            "Wrong sorting in query results"
        )


@pytest.mark.search_engine
@pytest.mark.django_db
def test_forum_empty_query(search_engine_forum_backend):
    """Test empty forum query returns results"""
    results = search_engine_forum_backend.search_forum_posts(textual_query="")
    assert results.num_found > 0, "Empty query returned no results"


@pytest.mark.search_engine
@pytest.mark.django_db
def test_forum_group_by_thread(search_engine_forum_backend):
    """Test forum post grouping by thread"""
    results = search_engine_forum_backend.search_forum_posts()
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
@pytest.mark.django_db
def test_forum_highlighting(search_engine_forum_backend):
    """Test forum post highlighting"""
    results = search_engine_forum_backend.search_forum_posts(textual_query="microphone")
    assert results.highlighting != dict(), "No highlighting entries returned"
    for highlighting_content in results.highlighting.values():
        assert "post_body" in highlighting_content, (
            "Highlighting data without expected fields"
        )


@contextmanager
def queryTimer():
    """Context manager to time a code block using time.monotonic. Returns elapsed time in seconds."""
    start = time.monotonic()
    elapsed = None
    try:
        yield lambda: elapsed
    finally:
        elapsed = time.monotonic() - start

