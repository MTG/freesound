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

import datetime
import logging
import os
import time

from django.conf import settings

import utils.search
from forum.models import Post
from sounds.models import Sound, Download
from utils.search import get_search_engine


console_logger = logging.getLogger("console")

def assert_and_continue(expression, error_message):
    if not expression:
        console_logger.info('Error: {}'.format(error_message))


class TestSearchEngineBackend():
    def __init__(self, backend_name, write_output):
        self.search_engine = get_search_engine(backend_class=backend_name)
        if write_output:
            base_dir = os.path.join(settings.DATA_PATH, 'search_backend_tests')
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
            date_label = datetime.datetime.today().strftime('%Y%m%d_%H%M')
            self.output_file = open(os.path.join(base_dir, '{}_test_results_{}.txt'
                                                .format(date_label, backend_name)), 'w')
            self.output_file.write('TESTING SEARCH ENGINE BACKEND: {}\n'.format(backend_name))
        else:
            self.output_file = None

    def save_query_results(self, results, query_data, elapsed_time, query_type):
        self.output_file.write('\n* QUERY {}: {} (took {:.2f} seconds)\n'.format(query_type, str(query_data), elapsed_time))
        self.output_file.write(
            'num_found: {}\nnon_grouped_number_of_results: {}\nq_time: {}\nfacets: {}\nhighlighting: {}\ndocs:\n'.format(
                results.num_found,
                results.non_grouped_number_of_results,
                results.q_time,
                results.facets,
                results.highlighting
            ))
        for count, doc in enumerate(results.docs):
            self.output_file.write('\t{}. {}: {}\n'.format(count + 1, doc['id'], doc))


    def run_sounds_query_and_save_results(self, query_data):
        """Run a sounds search query in the search engine, save and return the results

        Args:
            search_engine (utils.search.SearchEngineBase): search engine object for performing the test query
            query_data (dict): parameters for the search query

        Returns:
            utils.search.SearchResults: object with the query results
        """
        start = time.time()
        results = self.search_engine.search_sounds(**query_data)
        end = time.time()

        # Assert that the result is of the expected type
        assert_and_continue(type(results) == utils.search.SearchResults, 'Returned search results object of wrong type')

        # Save results to file so the later we can compare between different search engine backends
        if self.output_file:
            self.save_query_results(results, query_data, end - start, query_type='SOUNDS')

        return results


    def run_forum_query_and_save_results(self, query_data):
        """Run a forum posts search query in the search engine, save and return the results

        Args:
            search_engine (utils.search.SearchEngineBase): search engine object for performing the test query
            query_data (dict): parameters for the search query

        Returns:
            utils.search.SearchResults: object with the query results
        """
        start = time.time()
        results = self.search_engine.search_forum_posts(**query_data)
        end = time.time()

        # Assert that the result is of the expected type
        assert_and_continue(type(results) == utils.search.SearchResults, 'Returned search results object of wrong type')

        # Save results to file so the later we can compare between different search engine backends
        if self.output_file:
            self.save_query_results(results, query_data, end - start, query_type='FORUM POSTS')

        return results


    def sound_check_random_sound(self):
        # Get random sound IDs and make sure these are different
        # Note that there is a slight chance that this test fails because the same sound is chosen randomly two
        # times in a row, but the chances are very low
        last_id = 0
        for i in range(0, 10):
            new_id = self.search_engine.get_random_sound_id()
            assert_and_continue(new_id != last_id,
                                'Repeated sound IDs in subsequent calls to "get random sound id" method')
            last_id = new_id

    def sound_check_offsets(self):
        # Test num_sounds/offset/current_page parameters
        results = self.run_sounds_query_and_save_results(dict(num_sounds=10, offset=0))
        offset_0_ids = [r['id'] for r in results.docs]
        results = self.run_sounds_query_and_save_results(dict(num_sounds=10, offset=1))
        offset_1_ids = [r['id'] for r in results.docs]
        assert_and_continue(len(offset_0_ids) == 10, 'Unexpected num_sounds/offset/current_page behaviour')
        assert_and_continue(len(offset_1_ids) == 10, 'Unexpected num_sounds/offset/current_page behaviour')
        assert_and_continue(offset_0_ids[1:] == offset_1_ids[:-1],
                            'Unexpected num_sounds/offset/current_page behaviour')

        results = self.run_sounds_query_and_save_results(dict(num_sounds=1, offset=4))
        offset_4_num_sounds_1_ids = [r['id'] for r in results.docs]
        assert_and_continue(len(offset_4_num_sounds_1_ids) == 1,
                            'Unexpected num_sounds/offset/current_page behaviour')
        assert_and_continue(offset_0_ids[4] == offset_4_num_sounds_1_ids[0],
                            'Unexpected num_sounds/offset/current_page behaviour')

        results = self.run_sounds_query_and_save_results(dict(num_sounds=5, current_page=2))
        page_2_num_sounds_5_ids = [r['id'] for r in results.docs]
        assert_and_continue(len(page_2_num_sounds_5_ids) == 5,
                            'Unexpected num_sounds/offset/current_page behaviour')
        assert_and_continue(page_2_num_sounds_5_ids == offset_0_ids[5:],
                            'Unexpected num_sounds/offset/current_page behaviour')

    def sound_check_empty_query(self):
        # Test empty query returns results
        results = self.run_sounds_query_and_save_results(dict(textual_query=''))
        assert_and_continue(results.num_found > 0, 'Empty query returned no results')

    def sound_check_sort_parameter(self, test_sound_ids):
        # Test sort parameter (only use sounds within test_sound_ids to make sure these were indexed "correctly")
        # This also tests parameter only_sounds_within_ids
        for sort_option_web in settings.SEARCH_SOUNDS_SORT_OPTIONS_WEB:
            results = self.run_sounds_query_and_save_results(dict(sort=sort_option_web,
                                                                num_sounds=len(test_sound_ids),
                                                                only_sounds_within_ids=test_sound_ids))
            result_ids = [r['id'] for r in results.docs]
            sounds = Sound.objects.ordered_ids(result_ids)
            assert_and_continue(sorted(test_sound_ids) == sorted(result_ids),
                                'only_sounds_within_ids not respected')

            # Assert that sorting criteria is preserved
            for sound1, sound2 in zip(sounds[:-1], sounds[1:]):
                if sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_AUTOMATIC:
                    # Nothing to test here as there's no expected result
                    pass
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_MOST_FIRST:
                    assert_and_continue(Download.objects.filter(sound=sound1).count() >=
                                        Download.objects.filter(sound=sound2).count(),
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DOWNLOADS_LEAST_FIRST:
                    assert_and_continue(Download.objects.filter(sound=sound1).count() <=
                                        Download.objects.filter(sound=sound2).count(),
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DATE_OLD_FIRST:
                    assert_and_continue(sound1.created <= sound2.created,
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DATE_NEW_FIRST:
                    assert_and_continue(sound1.created >= sound2.created,
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_RATING_LOWEST_FIRST:
                    assert_and_continue(sound1.avg_rating <= sound2.avg_rating,
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_RATING_HIGHEST_FIRST:
                    assert_and_continue(sound1.avg_rating >= sound2.avg_rating,
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_LONG_FIRST:
                    assert_and_continue(sound1.duration >= sound2.duration,
                                        'Wrong ordering in {}'.format(sort_option_web))
                elif sort_option_web == settings.SEARCH_SOUNDS_SORT_OPTION_DURATION_SHORT_FIRST:
                    assert_and_continue(sound1.duration <= sound2.duration,
                                        'Wrong ordering in {}'.format(sort_option_web))

    def sound_check_group_by_pack(self):
        # Test group by pack
        results = self.run_sounds_query_and_save_results(dict(group_by_pack=True))
        for result in results.docs:
            assert_and_continue('id' in result, 'No ID field in doc from results')
            assert_and_continue('group_name' in result, 'No group_name field in doc from results')
            assert_and_continue('group_docs' in result, 'No group_docs field in doc from results')
            assert_and_continue('n_more_in_group' in result, 'No n_more_in_group field in doc from results')
            group_sounds = Sound.objects.bulk_query_id(sound_ids=[r['id'] for r in result['group_docs']])
            first_sound_pack = group_sounds[0].pack
            for sound in group_sounds:
                assert_and_continue(sound.pack == first_sound_pack, 'Different packs in pack group')

    def sound_check_sounds_with_pack(self):
        # Test only sounds with pack
        results = self.run_sounds_query_and_save_results(dict(only_sounds_with_pack=True, num_sounds=50))
        sounds = Sound.objects.bulk_query_id(sound_ids=[r['id'] for r in results.docs])
        for sound in sounds:
            assert_and_continue(sound.pack is not None, 'Sound without pack when using "only_sounds_with_pack"')

    def sound_check_facets(self):
        # Test facets included in results
        test_facet_options = {
            settings.SEARCH_SOUNDS_FIELD_USER_NAME: {'limit': 3},
            settings.SEARCH_SOUNDS_FIELD_SAMPLERATE: {'limit': 1},
            settings.SEARCH_SOUNDS_FIELD_TYPE: {},
        }
        results = self.run_sounds_query_and_save_results(dict(facets=test_facet_options))
        assert_and_continue(len(results.facets) == 3, 'Wrong number of facets returned')
        for facet_field, facet_options in test_facet_options.items():
            assert_and_continue(facet_field in results.facets, 'Facet {} not found in facets'.format(facet_field))
            if 'limit' in facet_options:
                assert_and_continue(len(results.facets[facet_field]) == facet_options['limit'],
                                    'Wrong number of items in facet {}'.format(facet_field))

        # Test if no facets requested, no facets returned
        results = self.run_sounds_query_and_save_results(dict())
        assert_and_continue(results.facets == dict(), 'Facets returned but not requested')

    def sound_check_extra_queries(self):
        # Run a couple of extra queries without assessing results so that these get saved and the results can be
        # later manually compared with results from other search backends
        self.run_sounds_query_and_save_results(dict(textual_query='dog'))
        self.run_sounds_query_and_save_results(dict(textual_query='microphone'))
        self.run_sounds_query_and_save_results(dict(textual_query='piano loop'))
        self.run_sounds_query_and_save_results(dict(textual_query='explosion'))

    def test_search_enginge_backend_sounds(self):
        # Get sounds for testing
        test_sound_ids = list(Sound.public
                                .filter(is_index_dirty=False, num_ratings__gt=settings.MIN_NUMBER_RATINGS)
                                .values_list('id', flat=True)[0:20])
        sounds = list(Sound.objects.bulk_query_solr(test_sound_ids))
        if len(sounds) < 20:
            raise Exception("Can't test SearchEngine backend as there are not enough sounds for testing")

        # Remove sounds from the search index (in case sounds are there)
        self.search_engine.remove_sounds_from_index(sounds)
        for sound in sounds:
            assert_and_continue(not self.search_engine.sound_exists_in_index(sound),
                                'Sound ID {} should not be in the search index'.format(sound.id))

        # Index the sounds again
        self.search_engine.add_sounds_to_index(sounds)

        # Check that sounds are indexed (test with sound object and with ID)
        for sound in sounds:
            assert_and_continue(self.search_engine.sound_exists_in_index(sound),
                                'Sound ID {} should be in the search index'.format(sound.id))
            assert_and_continue(self.search_engine.sound_exists_in_index(sound.id),
                                'Sound ID {} should be in the search index'.format(sound.id))

        # Remove some sounds form the ones just indexed and check they do not exist
        removed_sounds_by_sound_object = sounds[0:3]
        self.search_engine.remove_sounds_from_index(removed_sounds_by_sound_object)
        for sound in removed_sounds_by_sound_object:
            assert_and_continue(not self.search_engine.sound_exists_in_index(sound),
                                'Sound ID {} should not be in the search index'.format(sound.id))
        removed_sounds_by_sound_id = [s.id for s in sounds[3:6]]
        self.search_engine.remove_sounds_from_index(removed_sounds_by_sound_id)
        for sid in removed_sounds_by_sound_id:
            assert_and_continue(not self.search_engine.sound_exists_in_index(sid),
                                'Sound ID {} should not be in the search index'.format(sid))

        # Check that all sounds which were not removed are still in the index
        remaining_sounds = sounds[6:]
        for sound in remaining_sounds:
            assert_and_continue(self.search_engine.sound_exists_in_index(sound),
                                'Sound ID {} should be in search index'.format(sound.id))

        # Re-index all sounds to leave index in "correct" state
        self.search_engine.add_sounds_to_index(sounds)


        self.sound_check_random_sound()
        self.sound_check_offsets()
        self.sound_check_empty_query()
        self.sound_check_sort_parameter(test_sound_ids)
        self.sound_check_group_by_pack()
        self.sound_check_sounds_with_pack()
        self.sound_check_facets()
        self.sound_check_extra_queries()

        console_logger.info('Testing of sound search methods finished. You might want to run the '
                            'reindex_search_engine_sounds -c command to make sure the index is left in a correct '
                            'state after having run these tests')

    def forum_check_offsets(self):
        # Test num_posts/offset/current_page parameters
        results = self.run_forum_query_and_save_results(dict(num_posts=10, offset=0))
        offset_0_ids = [r['id'] for r in results.docs]
        results = self.run_forum_query_and_save_results(dict(num_posts=10, offset=1))
        offset_1_ids = [r['id'] for r in results.docs]
        assert_and_continue(len(offset_0_ids) == 10, 'Unexpected num_posts/offset/current_page behaviour 1')
        assert_and_continue(len(offset_1_ids) == 10, 'Unexpected num_posts/offset/current_page behaviour 2')
        assert_and_continue(offset_0_ids[1:] == offset_1_ids[:-1],
                            'Unexpected num_posts/offset/current_page behaviour 3')

        results = self.run_forum_query_and_save_results(dict(num_posts=1, offset=4))
        offset_4_num_sounds_1_ids = [r['id'] for r in results.docs]
        assert_and_continue(len(offset_4_num_sounds_1_ids) == 1,
                            'Unexpected num_posts/offset/current_page behaviour 4')
        assert_and_continue(offset_0_ids[4] == offset_4_num_sounds_1_ids[0],
                            'Unexpected num_posts/offset/current_page behaviour 5')

        results = self.run_forum_query_and_save_results(dict(num_posts=5, current_page=2))
        page_2_num_sounds_5_ids = [r['id'] for r in results.docs]
        assert_and_continue(len(page_2_num_sounds_5_ids) == 5,
                            'Unexpected num_posts/offset/current_page behaviour 6')
        assert_and_continue(page_2_num_sounds_5_ids == offset_0_ids[5:],
                            'Unexpected num_posts/offset/current_page behaviour 7')

        # Test that results are sorted by newest posts first. Also assess results have the required fields
        expected_fields = ["id", "forum_name", "forum_name_slug", "thread_id", "thread_title", "thread_author",
                            "thread_created", "post_body", "post_author", "post_created", "num_posts"]
        results = self.run_forum_query_and_save_results(dict(group_by_thread=False))
        for result1, result2 in zip(results.docs[:-1], results.docs[1:]):
            for field in expected_fields:
                assert_and_continue(field in result1, '{} not present in result ID {}'.format(field, result1['id']))
                assert_and_continue(result1["thread_created"] >= result2["thread_created"],
                                    'Wrong sorting in query results')

    def forum_check_empty_query(self):
        # Test empty query returns results
        results = self.run_forum_query_and_save_results(dict(textual_query=''))
        assert_and_continue(results.num_found > 0, 'Empty query returned no results')

    def forum_check_group_by_thread(self):
        # Test group by threads
        results = self.run_forum_query_and_save_results(dict())
        for result in results.docs:
            assert_and_continue('id' in result, 'No ID field in doc from results')
            assert_and_continue('group_name' in result, 'No group_name field in doc from results')
            assert_and_continue('group_docs' in result, 'No group_docs field in doc from results')
            assert_and_continue('n_more_in_group' in result, 'No n_more_in_group field in doc from results')

            first_post_thread = result["group_docs"][0]["thread_title"]
            for doc in result["group_docs"]:
                assert_and_continue(doc["thread_title"] == first_post_thread, 'Different threads in thread group')

    def forum_check_highlighting(self):
        # Test highlighting in results
        results = self.run_forum_query_and_save_results(dict(textual_query="microphone"))
        assert_and_continue(results.highlighting != dict(), 'No highlighting entries returned')
        for highlighting_content in results.highlighting.values():
            assert_and_continue('post_body' in highlighting_content, 'Highlighting data without expected fields')

    def forum_check_extra_queries(self):
        # Run a couple of extra queries without assessing results so that these get saved and the results can be
        # later manually compared with results from other search backends
        self.run_forum_query_and_save_results(dict(textual_query='microphone'))
        self.run_forum_query_and_save_results(dict(textual_query='technique'))
        self.run_forum_query_and_save_results(dict(textual_query='freesound'))    

    def test_search_enginge_backend_forum(self):
        # Get posts for testing
        test_post_ids = list(Post.objects.filter(moderation_state="OK").values_list('id', flat=True)[0:20])
        posts = list(Post.objects.filter(id__in=test_post_ids))
        if len(posts) < 20:
            raise Exception("Can't test SearchEngine backend as there are not enough forum posts for testing")

        # Remove posts from the search index (in case posts are there)
        self.search_engine.remove_forum_posts_from_index(posts)
        for post in posts:
            assert_and_continue(not self.search_engine.forum_post_exists_in_index(post),
                                'Post ID {} should not be in the search index'.format(post.id))

        # Index the posts again
        self.search_engine.add_forum_posts_to_index(posts)

        # Check that posts are indexed (test with sound object and with ID)
        for post in posts:
            assert_and_continue(self.search_engine.forum_post_exists_in_index(post),
                                'Post ID {} should be in the search index'.format(post.id))
            assert_and_continue(self.search_engine.forum_post_exists_in_index(post.id),
                                'Post ID {} should be in the search index'.format(post.id))

        # Remove some posts form the ones just indexed and check they do not exist
        removed_posts_by_post_object = posts[0:3]
        self.search_engine.remove_forum_posts_from_index(removed_posts_by_post_object)
        for post in removed_posts_by_post_object:
            assert_and_continue(not self.search_engine.forum_post_exists_in_index(post),
                                'Post ID {} should not be in the search index'.format(post.id))
        removed_posts_by_post_id = [s.id for s in posts[3:6]]
        self.search_engine.remove_forum_posts_from_index(removed_posts_by_post_id)
        for pid in removed_posts_by_post_id:
            assert_and_continue(not self.search_engine.forum_post_exists_in_index(pid),
                                'Post ID {} should not be in the search index'.format(pid))

        # Check that all posts which were not removed are still in the index
        remaining_posts = posts[6:]
        for post in remaining_posts:
            assert_and_continue(self.search_engine.forum_post_exists_in_index(post),
                                'Post ID {} should be in search index'.format(post.id))

        # Re-index all posts to leave index in "correct" state
        self.search_engine.add_forum_posts_to_index(posts)

        self.forum_check_offsets()
        self.forum_check_empty_query()
        self.forum_check_group_by_thread()
        self.forum_check_highlighting()
        self.forum_check_extra_queries()

        console_logger.info('Testing of forum search methods finished. You might want to run the '
                            'reindex_search_engine_forum -c command to make sure the index is left in a correct '
                            'state after having run these tests')
