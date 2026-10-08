from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from user_feedback.experiments import CategoryFilterFeedback, CategoryValidation, Experiment
from user_feedback.models import FeedbackOptOut, UserFeedback
from utils.search.search_query_processor import SearchQueryProcessor
from utils.test_helpers import create_user_and_sounds


class _ToyExperiment(Experiment):
    """Test-only experiment: exercises the generic base seam in isolation, with no
    dependency on real models/context. Proves the machinery is reusable. Not shipped."""

    experiment_id = "toy"


class _FakeSound:
    """Duck-typed stand-in: is_context_eligible only reads .bst_category, so a real Sound is not needed here."""

    def __init__(self, bst_category):
        self.bst_category = bst_category


@override_settings(FEEDBACK_EXPERIMENTS={"toy": {"sample_rate": 1.0}})
class ExperimentBaseTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user("alice", email="alice@freesound.org", password="testpass")

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_anonymous_never_shown(self):
        self.assertFalse(_ToyExperiment().should_show(self._request(AnonymousUser())))

    @override_settings(FEEDBACK_EXPERIMENTS={"toy": {"sample_rate": 0.0}})
    def test_rate_zero_never_sampled(self):
        self.assertFalse(_ToyExperiment().is_sampled_in(self._request(self.user)))

    def test_rate_one_always_sampled(self):
        self.assertTrue(_ToyExperiment().is_sampled_in(self._request(self.user)))

    @override_settings(FEEDBACK_EXPERIMENTS={"toy": {"sample_rate": 0.5}})
    def test_sampling_is_deterministic(self):
        experiment = _ToyExperiment()
        request = self._request(self.user)
        # Same user -> same verdict every time (no re-rolling per page load).
        self.assertEqual(experiment.is_sampled_in(request), experiment.is_sampled_in(request))

    def test_throttled_after_answering(self):
        experiment = _ToyExperiment()
        request = self._request(self.user)
        self.assertTrue(experiment.should_show(request))  # shown before answering
        experiment.save_response(self.user, {"answer": "yes"})  # yes/no only
        self.assertFalse(experiment.should_show(request))  # not shown again after

    def test_opt_out_hides_it(self):
        experiment = _ToyExperiment()
        request = self._request(self.user)
        self.assertTrue(experiment.should_show(request))  # shown before
        experiment.opt_out(self.user)  # "don't ask again"
        self.assertTrue(experiment.has_opted_out(self.user))
        self.assertFalse(experiment.should_show(request))  # hidden, permanently

    def test_category_validation_needs_a_category(self):
        experiment = CategoryValidation()
        request = self._request(self.user)
        self.assertFalse(experiment.is_context_eligible(request, sound=None))
        self.assertFalse(experiment.is_context_eligible(request, sound=_FakeSound("")))
        self.assertTrue(experiment.is_context_eligible(request, sound=_FakeSound("music")))


class SubmitAndModalViewTest(TestCase):
    """The generic submit + modal views, driven through their real URLs with the
    test client -- i.e. exactly what the box and modal hit in the browser."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, sounds = create_user_and_sounds(bst_category="fx-o")
        self.sound = sounds[0]
        self.client.force_login(self.user)
        self.submit_url = reverse("user-feedback-submit")
        self.modal_url = reverse("user-feedback-modal")

    def _rows(self):
        return UserFeedback.objects.filter(experiment_id="category_validation")

    def _submit(self, ajax=False, **data):
        data.setdefault("experiment_id", "category_validation")
        data.setdefault("sound_id", self.sound.id)
        return self.client.post(self.submit_url + ("?ajax=1" if ajax else ""), data)

    # -- submit: saved answers --
    def test_yes_saves_row_and_redirects(self):
        response = self._submit(answer="yes")
        self.assertEqual(response.status_code, 302)
        row = self._rows().get()
        self.assertEqual(row.user, self.user)
        # cleaned_data of the whole form is stored; the two extras are empty for "yes".
        self.assertEqual(row.data, {"answer": "yes", "sound_id": self.sound.id, "selected_category": "", "text": ""})

    def test_yes_ajax_returns_json(self):
        response = self._submit(ajax=True, answer="yes")
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response["content-type"])
        self.assertEqual(self._rows().count(), 1)

    def test_yes_drops_a_leftover_category(self):
        # Picking a category under "no" and then switching to "yes" still posts it.
        self._submit(ajax=True, answer="yes", selected_category="ss-n")
        self.assertEqual(self._rows().get().data["selected_category"], "")

    def test_yes_drops_a_leftover_top_level_category(self):
        # Top level only ("ss") is not a valid choice, but a "yes" must still save.
        response = self._submit(ajax=True, answer="yes", selected_category="ss")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._rows().get().data["selected_category"], "")

    def test_no_with_category_saves(self):
        response = self._submit(ajax=True, answer="no", selected_category="ss-n", text="wrong one")
        self.assertIn("application/json", response["content-type"])
        row = self._rows().get()
        self.assertEqual(row.data["answer"], "no")
        self.assertEqual(row.data["selected_category"], "ss-n")
        self.assertEqual(row.data["text"], "wrong one")

    # -- submit: client ip --
    @override_settings(DEBUG=False)
    def test_submit_stores_forwarded_ip(self):
        self.client.post(
            self.submit_url,
            {"experiment_id": "category_validation", "sound_id": self.sound.id, "answer": "yes"},
            HTTP_X_FORWARDED_FOR="5.6.7.8",
        )
        self.assertEqual(self._rows().get().ip, "5.6.7.8")

    @override_settings(DEBUG=False)
    def test_submit_without_proxy_header_stores_no_ip(self):
        # get_client_ip returns "-" with no header; the view stores NULL, not "-"
        # (which the ip column would reject).
        self.client.post(
            self.submit_url,
            {"experiment_id": "category_validation", "sound_id": self.sound.id, "answer": "yes"},
        )
        self.assertIsNone(self._rows().get().ip)

    # -- submit: rejected, nothing saved --
    def test_no_without_category_is_rejected(self):
        response = self._submit(ajax=True, answer="no")
        # Rejected ajax submit returns a 400, so the caller can't mistake it for a save.
        self.assertEqual(response.status_code, 400)
        self.assertIn("application/json", response["content-type"])
        self.assertEqual(
            response.json()["errors"]["selected_category"][0]["message"], "Please choose a category and subcategory."
        )
        self.assertEqual(self._rows().count(), 0)

    def test_no_with_only_top_level_category_is_rejected(self):
        # Top-level only ("ss") is not a subcategory choice; it gets the same readable message.
        response = self._submit(ajax=True, answer="no", selected_category="ss")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["errors"]["selected_category"][0]["message"], "Please choose a category and subcategory."
        )
        self.assertEqual(self._rows().count(), 0)

    def test_tampered_sound_id_is_rejected(self):
        response = self._submit(ajax=True, answer="yes", sound_id=999999999)
        self.assertEqual(response.status_code, 400)
        self.assertIn("sound_id", response.json()["errors"])
        self.assertEqual(self._rows().count(), 0)

    def test_unknown_experiment_returns_404(self):
        self.assertEqual(self._submit(experiment_id="does-not-exist", answer="yes").status_code, 404)

    # -- submit: method / auth guards --
    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.submit_url).status_code, 405)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        response = self._submit(answer="yes")
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response["Location"])
        self.assertEqual(self._rows().count(), 0)

    # -- modal view (generic) --
    def test_modal_unknown_experiment_404(self):
        self.assertEqual(self.client.get(self.modal_url, {"experiment_id": "nope"}).status_code, 404)

    # -- opt-out view --
    def _opt_out(self, **data):
        data.setdefault("experiment_id", "category_validation")
        return self.client.post(reverse("user-feedback-opt-out"), data)

    def test_opt_out_records_row_and_redirects(self):
        response = self._opt_out()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(FeedbackOptOut.objects.filter(user=self.user, experiment_id="category_validation").exists())

    def test_opt_out_is_idempotent(self):
        self._opt_out()
        self._opt_out()  # clicking twice must not create two rows
        self.assertEqual(FeedbackOptOut.objects.filter(user=self.user, experiment_id="category_validation").count(), 1)

    def test_opt_out_unknown_experiment_404(self):
        self.assertEqual(self._opt_out(experiment_id="nope").status_code, 404)

    def test_opt_out_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("user-feedback-opt-out")).status_code, 405)


@override_settings(FEEDBACK_EXPERIMENTS={"category_validation": {"sample_rate": 1.0}})
class PerSoundThrottleTest(TestCase):
    """Answering about one sound must not stop the box appearing on other sounds:
    category_validation throttles per sound, not once per user like the base class."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, self.sounds = create_user_and_sounds(num_sounds=2, bst_category="fx-o")
        self.experiment = CategoryValidation()

    def _request(self):
        request = RequestFactory().get("/")
        request.user = self.user
        return request

    def test_answering_one_sound_does_not_throttle_another(self):
        first, second = self.sounds
        request = self._request()
        self.assertTrue(self.experiment.should_show(request, sound=first))
        self.assertTrue(self.experiment.should_show(request, sound=second))

        self.experiment.save_response(self.user, {"answer": "yes", "sound_id": first.id})

        self.assertFalse(self.experiment.should_show(request, sound=first))  # answered -> hidden
        self.assertTrue(self.experiment.should_show(request, sound=second))  # untouched -> still shown

    def test_opt_out_hides_every_sound(self):
        first, second = self.sounds
        request = self._request()
        self.assertTrue(self.experiment.should_show(request, sound=first))
        self.experiment.opt_out(self.user)  # "don't ask again" -> hides all sounds
        self.assertFalse(self.experiment.should_show(request, sound=first))
        self.assertFalse(self.experiment.should_show(request, sound=second))


@override_settings(FEEDBACK_EXPERIMENTS={"category_validation": {"sample_rate": 0.5}})
class PerUserSoundSamplingTest(TestCase):
    """category_validation samples per (user, sound): every user can be asked and the
    rate gates each sound they open, rather than a fixed cohort of users."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, self.sounds = create_user_and_sounds(num_sounds=2, bst_category="fx-o")
        self.experiment = CategoryValidation()

    def _request(self):
        request = RequestFactory().get("/")
        request.user = self.user
        return request

    def test_key_depends_on_both_user_and_sound(self):
        request = self._request()
        first, second = self.sounds
        key_first = self.experiment.sampling_key(request, sound=first)
        self.assertIn(str(self.user.id), key_first)
        self.assertIn(str(first.id), key_first)
        # same user, different sound -> different key (so the rate is rolled per sound)
        self.assertNotEqual(key_first, self.experiment.sampling_key(request, sound=second))

    def test_verdict_is_stable_for_same_user_and_sound(self):
        request = self._request()
        sound = self.sounds[0]
        # deterministic: same (user, sound) lands the same way on every page load
        self.assertEqual(
            self.experiment.is_sampled_in(request, sound=sound),
            self.experiment.is_sampled_in(request, sound=sound),
        )


class RenderInlineHtmlTest(TestCase):
    """render_inline_html: the experiment renders its own box, so the host page just
    outputs the string (empty when it should not show) and stays experiment-agnostic."""

    fixtures = ["licenses"]

    def setUp(self):
        self.user, _, sounds = create_user_and_sounds(bst_category="fx-o")
        self.sound = sounds[0]
        self.experiment = CategoryValidation()

    def _request(self):
        request = RequestFactory().get("/")
        request.user = self.user
        return request

    @override_settings(FEEDBACK_EXPERIMENTS={"category_validation": {"sample_rate": 1.0}})
    def test_renders_box_when_shown(self):
        html = self.experiment.render_inline_html(self._request(), sound=self.sound)
        self.assertIn("data-experiment-box", html)
        self.assertIn('name="selected_category"', html)  # the correction form is built in
        # Check the category links to its description in the taxonomy page
        self.assertIn(reverse("bst-info-page") + "#fx-o", html)

    @override_settings(FEEDBACK_EXPERIMENTS={"category_validation": {"sample_rate": 0.0}})
    def test_empty_string_when_not_shown(self):
        self.assertEqual(self.experiment.render_inline_html(self._request(), sound=self.sound), "")


@override_settings(FEEDBACK_EXPERIMENTS={"category_filter_feedback": {"sample_rate": 1.0}})
class CategoryFilterFeedbackTest(TestCase):
    """Tests for the category filter experiment of the search page."""

    fixtures = ["licenses"]
    # Info about the search that is sent with every answer
    SEARCH = {
        "category": "Music",
        "query": "piano",
        "search_filter": 'category:"Music"',
        "sort": "Automatic by relevance",
        "page": 1,
        "search_url": "/search/?q=piano&f=category%3A%22Music%22",
        "search_id": "miao123",
    }

    def setUp(self):
        # One page of search results
        self.user, _, self.sounds = create_user_and_sounds(num_sounds=settings.SOUNDS_PER_PAGE)
        self.client.force_login(self.user)
        self.experiment = CategoryFilterFeedback()

    def _items(self, client=None, **params):
        # Get the HTML pieces of the experiment for a search page that shows the sounds.
        # By default the search is "piano" filtered by the Music category
        params = {
            "q": "piano",
            "f": 'category:"Music"',
            "experiment_path": reverse("sounds-search"),
            "experiment_sound_ids": ",".join(str(sound.id) for sound in self.sounds),
            **params,
        }
        response = (client or self.client).get(reverse("user-feedback-page-items"), params)
        return response.json()["items"]

    def _submit(self, **data):
        data = {
            "experiment_id": "category_filter_feedback",
            "result_ids": ",".join(str(sound.id) for sound in self.sounds),
            **self.SEARCH,
            **data,
        }
        return self.client.post(reverse("user-feedback-submit") + "?ajax=1", data)

    def _rows(self):
        return UserFeedback.objects.filter(experiment_id="category_filter_feedback")

    def test_overall_answer_saves(self):
        # Check rating, comment and search info are saved
        response = self._submit(kind="overall", rating="4", text="handy")
        self.assertEqual(response.status_code, 200)
        data = self._rows().get().data
        self.assertEqual(data["kind"], "overall")
        self.assertEqual(data["rating"], 4)
        self.assertEqual(data["text"], "handy")
        self.assertEqual(data["category"], "Music")
        self.assertEqual(data["search_url"], self.SEARCH["search_url"])
        self.assertEqual(data["result_ids"], [sound.id for sound in self.sounds])
        # Check "result" fields are not saved
        self.assertNotIn("answer", data)

    def test_result_answer_saves(self):
        # Check yes/no, sound and position are saved
        sound = self.sounds[2]
        response = self._submit(kind="result", answer="no", sound_id=sound.id, position=3)
        self.assertEqual(response.status_code, 200)
        data = self._rows().get().data
        self.assertEqual(data["kind"], "result")
        self.assertEqual(data["answer"], "no")
        self.assertEqual(data["sound_id"], sound.id)
        self.assertEqual(data["position"], 3)
        # Check "overall" fields are not saved
        self.assertNotIn("rating", data)

    def test_incomplete_answers_are_rejected(self):
        # Try overall answer without rating
        self.assertIn("rating", self._submit(kind="overall").json()["errors"])
        # Try result answer without yes/no
        self.assertIn("answer", self._submit(kind="result", sound_id=self.sounds[0].id, position=1).json()["errors"])
        # Try result answer for unknown sound
        errors = self._submit(kind="result", answer="yes", sound_id=999999999, position=1).json()["errors"]
        self.assertIn("sound_id", errors)
        # Check nothing was saved
        self.assertEqual(self._rows().count(), 0)

    def test_results_get_the_question(self):
        items = self._items()
        # Check all the results of the page get the question
        questions = [item for item in items if "target" in item]
        self.assertEqual(len(questions), len(self.sounds))
        # Check the question has the sound and its position
        self.assertEqual(questions[0]["target"], f'[data-sound-id="{self.sounds[0].id}"]')
        self.assertIn(f'name="sound_id" value="{self.sounds[0].id}"', questions[0]["html"])
        self.assertIn('name="position" value="1"', questions[0]["html"])
        # Check the last piece has the search info
        self.assertIn('name="category" value="Music"', items[-1]["html"])
        self.assertIn('name="query" value="piano"', items[-1]["html"])
        # Check the results of another page get the question too
        items = self._items(page=2)
        self.assertEqual(len(items), len(self.sounds) + 1)
        self.assertIn('name="page" value="2"', items[-1]["html"])

    def test_no_question_when_it_should_not_show(self):
        # Search without category filter
        self.assertEqual(self._items(f=""), [])
        # Anonymous user
        self.assertEqual(self._items(client=Client()), [])
        # Page that has no experiment
        self.assertEqual(self._items(experiment_path=reverse("front-page")), [])
        # User opted out
        self.experiment.opt_out(self.user)
        self.assertEqual(self._items(), [])

    def test_answered_result_is_not_asked_again(self):
        answered = f'[data-sound-id="{self.sounds[2].id}"]'
        self._submit(kind="result", answer="yes", sound_id=self.sounds[2].id, position=3)
        # Check the answered result has no question, but the others do
        targets = [item.get("target") for item in self._items()]
        self.assertNotIn(answered, targets)
        self.assertEqual(len(targets), len(self.sounds))
        # Check it is asked again for a different query
        targets = [item.get("target") for item in self._items(q="guitar")]
        self.assertIn(answered, targets)

    def test_rating_bar_is_shown_until_rated(self):
        # Check the last piece has the bar, with the info modal and the opt-out
        html = self._items()[-1]["html"]
        self.assertIn("data-experiment-bar", html)
        self.assertIn("How useful was filtering by the", html)
        self.assertIn("Music</a> category?", html)
        self.assertIn("data-experiment-optout", html)
        # Check the bar is not shown again after rating this search, but the questions are
        self._submit(kind="overall", rating="4")
        items = self._items()
        self.assertNotIn("data-experiment-bar", items[-1]["html"])
        self.assertEqual(len(items), len(self.sounds) + 1)
        # Check the bar is shown again for another search in the same category
        self.assertIn("data-experiment-bar", self._items(q="guitar")[-1]["html"])

    def test_sampling_is_per_search(self):
        def key(**params):
            request = RequestFactory().get(reverse("sounds-search"), {"q": "piano", "f": 'category:"Music"', **params})
            request.user = self.user
            return self.experiment.sampling_key(request, sqp=SearchQueryProcessor(request))

        # Check the pages of a search have the same key
        self.assertEqual(key(), key(page=2))
        # Check another query or another category has a different key
        self.assertNotEqual(key(), key(q="guitar"))
        self.assertNotEqual(key(), key(f='category:"Speech"'))

    def test_subcategory_is_asked_separately(self):
        subcategory_filter = 'category:"Music" subcategory:"Solo percussion"'
        # Check the bar names the subcategory when it is selected
        html = self._items(f=subcategory_filter)[-1]["html"]
        self.assertIn("Music > Solo percussion</a> category?", html)
        # Check it links to the subcategory in the taxonomy page
        self.assertIn(reverse("bst-info-page") + "#m-sp", html)
        # Rate the category and answer one result, without subcategory
        self._submit(kind="overall", rating="4")
        self._submit(kind="result", answer="yes", sound_id=self.sounds[0].id, position=1)
        # Check the bar and all the results are still asked with the subcategory
        items = self._items(f=subcategory_filter)
        self.assertIn("data-experiment-bar", items[-1]["html"])
        self.assertEqual(len(items), len(self.sounds) + 1)
