import unittest

import mock

from similarity import client


class SimilarityClientTest(unittest.TestCase):

    def setUp(self):
        self.client = client.Similarity("localhost")

    @mock.patch('similarity.client._get_url_as_json')
    def test_search(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        r = self.client.search(1)

        self.assertEqual(r, {"data": "here"})
        # requests.Request('GET', 'url', params=params).prepare().url
        get_url.assert_called_with("http://localhost/similarity/nnsearch/?sound_id=1")
        get_url.reset_mock()

        self.client.search(1, num_results=10, preset='pr', offset=3)
        get_url.assert_called_with("http://localhost/similarity/nnsearch/?sound_id=1&num_results=10&preset=pr&offset=3")

    @mock.patch('similarity.client._get_url_as_json')
    def test_api_search(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.api_search()
        get_url.assert_called_with("http://localhost/similarity/api_search/?", data=None)
        get_url.reset_mock()

        self.client.api_search(target_type=1, target=2, filter=3, preset=4, metric_descriptor_names=5,
                               num_results=6, offset=7, file='x', in_ids="7,8,9")
        get_url.assert_called_with("http://localhost/similarity/api_search/?&target_type=1&target=2&filter=3&preset=4&metric_descriptor_names=5&num_results=6&offset=7&in_ids=7,8,9", data="x")

    @mock.patch('similarity.client._get_url_as_json')
    def test_add(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.add(10, 'data.yaml')
        get_url.assert_called_with("http://localhost/similarity/add_point/?sound_id=10&location=data.yaml")

    @mock.patch('similarity.client._get_url_as_json')
    def test_get_all_sound_ids(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.get_all_sound_ids()
        get_url.assert_called_with("http://localhost/similarity/get_all_point_names/")

    @mock.patch('similarity.client._get_url_as_json')
    def test_get_descriptor_names(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.get_descriptor_names()
        get_url.assert_called_with("http://localhost/similarity/get_descriptor_names/")

    @mock.patch('similarity.client._get_url_as_json')
    def test_delete(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.delete(123)
        get_url.assert_called_with("http://localhost/similarity/delete_point/?sound_id=123")

    @mock.patch('similarity.client._get_url_as_json')
    def test_save(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.save()
        get_url.assert_called_with("http://localhost/similarity/save/", timeout=300)
        get_url.reset_mock()

        self.client.save('database.db')
        get_url.assert_called_with("http://localhost/similarity/save/?filename=database.db", timeout=300)

    @mock.patch('similarity.client._get_url_as_json')
    def test_get_sounds_descriptors(self, get_url):
        get_url.return_value = {"error": False, "result": {"data": "here"}}

        self.client.get_sounds_descriptors([1, 2, 3])
        get_url.assert_called_with("http://localhost/similarity/get_sounds_descriptors/?sound_ids=1,2,3&normalization=1")
