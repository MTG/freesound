# Freesound Developer notes

## Code layout
Where possible, use consistent formatting for file layout. In pycharm take advantage of the 
`Code`→`Optimize imports` and `Code`→`Reformat code` menu items in order to have a consistent 
code layout.

## Code documentation
We use Google-style docstrings.
You can see examples of these docstrings here: 
https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html

In pycharm you can set this format by choosing in Preferences `Tools`→`Python Integrated Tools` 
and change the Docstring format.

Make sure whenever possible you add type annotations to the variables, e.g.

    Args:
        param1 (int): The first parameter.

Always use a . to end sentences of a docstring. This includes argument lists 
and other lists (see the Google example linked above). Here is an example of one
of the docstrings in our code base that you can use as reference
(from `utils.test_helpers.create_user_and_sounds`):

```
"""Creates User, Sound and Pack objects useful for testing.

A counter is used to make sound names unique as well as other fields like md5 (see `sound_counter` variable).
NOTE: creating sounds requires License objects to exist in DB. Do that by making sure your test case loads
'licenses' fixture, i.e. "fixtures = ['licenses']".

Args:
    num_sounds (int): N sounds to generate.
    num_packs (int): N packs in which the sounds above will be grouped.
    user (User): user owner of the created sounds (if not provided, a new user will be created).
    count_offset (int): start counting sounds at X.
    tags (str): string of tags to be added to the sounds (all sounds will have the same tags).
    processing_state (str): processing state of the created sounds.
    moderation_state (str): moderation state of the created sounds.
    type (str): type of the sounds to be created (e.g. 'wav').

Returns:
    (Tuple(User, List[Pack], List[Sound]): 3-element tuple containing the user owning the sounds,
        a list of the packs created and a list of the sounds created.
"""
```

## Making changes
Prefer to create a pull request for all changes. This allows us to keep a record of the changes 
that were made, and allow feedback if necessary


## Specific notes

### Custom Django permissions

If there is a need for defining custom permissions we should define them in the corresponding model's `Meta` class
as [described in the Django docs](https://docs.djangoproject.com/en/dev/topics/auth/customizing/#custom-permissions). There
is no generic model to **host** all custom permissions, but we'll add them to the most closely related model. These
permissions should then be added to a `Group` so that we can manage them properly in the Django admin. The `Group` should
be added in the [`user_groups`](https://github.com/MTG/freesound/blob/master/accounts/fixtures/user_groups.json)
fixture and then the fixture needs to be manually loaded to the database. Loading the fixture won't duplicate
groups which are already existing if the `pk` is specified in the fixture.


NOTE: Currently this fixture needs to be loaded manually to the database. We have plans for writing a command that will
automatically load the important fixtures (in the past Django used to do that automatically with fixtures named `initial_data`).

Currently, we only use the following custom permissions:
* `tickets.can_moderate` (in `Ticket` model, used to allow sound moderation)
* `forum.can_moderate_forum` (in `Post` model, used to allow forum moderation)
* `sounds.can_describe_in_bulk` (in `BulkUploadProgress` model, used to allow bulk upload for users who don't meet the other common requirements)
* `profile.can_beta_test` (in `Profile` model, used to allow using beta search features)


### URLs that include a username

There are many URLs in Freesound which include usernames in the path. For example, the sound page has an URL like
`freesound.org/people/<username>/sounds/<sound_id>`. This is because we want to give strong presence of usernames
in URLs to reinforce the attribution concept present in Creative Commons licenses.
When a URL includes a username we try match it with a `User` object in our database. For this we have to take into
account a number of things:

* Whether there is indeed a `User` object with that `username` property in the DB
* In case a user object exists, is the user marked as having been deleted? (check `user.profile.is_anonymized_user`) 
* In case there's no `User` object with such username, is there any `OldUsername` object which maps the username in the
  URL with a `User` object in DB?
  
To deal with these checks, we use the `utils.username.raise_404_if_user_is_deleted` and 
`utils.username.redirect_if_old_username_or_404` decorators in view functions. The first one will try to find a user
object (checking for old usernames as well) and if it can't find it or the user is marked as deleted, it will raise
HTTP 404 error. The second one will try to find a user object (also considering old usernames) and do an HTTP redirect
with an updated username if user was found in the old usernames table.

In general, we should use `utils.username.redirect_if_old_username_or_404` in **all public views** that have username
in the URL path. For login-required views (using `@login_required` decorator) we are not supposed to use that decorator
because most of them won't include username in the URL and also there should be no links pointing to these URLs with
old usernames. In addition, **if these public views should should not be reachable in case users have been anonymized**,
then we should also use `utils.username.raise_404_if_user_is_deleted`. When using both in combination, it is important
to use them in that order:

```
@redirect_if_old_username_or_404
@raise_404_if_user_is_deleted
def view_function(request, username, ...):
    ...
```


### About Django database migrations

We should aim to minimise the amount of downtime due to database migrations. This means that instead of doing complex 
data migration in a migration file, we should consider doing a basic migration, copying data in a management command, 
and then using the data. This may require that we do multiple releases to get all data populated and the site using 
this data.

For tables that have lots of rows, **adding a column** with a default value takes a long time. Adding this column as 
nullable is much faster. We can create a second migration to make the column not null once it is populated.


### Adding new fields to the user Profile model

When adding new fields to the `accounts.Profile` model, we should make sure that we also take care of these new fields 
in the `accounts.Profile.delete_user` method (which anonymizes a user account).


### Adding new fields to the user Sound model

When adding new fields to the `sounds.Sound` mode, we should make sure that we handle this fields correctly when 
creating `DeletedSound` objects in the `sounds-models.on_delete_sound` function triggered by the `pre_delete` 
signal of the `Sound` model.


### Adding new search options in the search page

The available options for searching and filtering sounds in the search page ara managed using a `SearchQueryProcessor`
object (implemented in `/utils/search/search_query_processor.py`). The `SearchQueryProcessor` class is used to parse and 
process search query information from a Django `request` object, and compute a number of useful items for displaying search 
information in templates, constructing search URLs, and preparing search options to be passed to the backend search engine.

To add a new option to the search page, a new member of a specific `SearchOption` class should be added to the `SearchQueryProcessor` 
class (see `SearchQueryProcessor` definion for examples). There are a number of already existing types of `SearchOption`s 
as you can see by looking at the search options which are already implemented in `SearchQueryProcessor`. If the newly added search
option implies doing some calcualtions for determining the `query_params` to be sent to the `search_sounds` function of the search 
engine backend, this should be done in the `SearchQueryProcessor.as_query_params` method.

Adding a new search option to `SearchQueryProcessor` will make the option work with the search engine backend and with search URLs, 
but it will NOT automatically add the option to the form in the search page. This will need to be done manually by adding the 
search option in the desired place in `templates/search/search.html` (see how other search options are implemented for inspiration,
there is a `display_search_option` templatetag which will facilitate things in most cases).

All this will add the search option to the user interface and send corresponding information to the search backend. For example,
if the new search option should apply a filter in the search backend of some `new_property`, this will be handled by the `SearchQueryProcessor`.
However, it is expected that this `new_property` has been added to the search engine schema and indexed properly, otherwise there
will be errors when running the queries.

Please have a look at the documentation of `SearchQueryProcessor` and the various `SearchOption` classes to get a better
understanding of how all this works.


### Search Engine Backends

The way in which Freesound communicates with a search engine to search for sounds and forum posts is abstracted through
the utils.search.SearchEngineBase class. Freesound can use different search engines as long a *backend class* is
implemented as a subclass of the abstract utils.search.SearchEngineBase. The API of this class is defined in way
that tries to be agnostic of the actual search engine backend being used. Since Freesound 2 (2011), we have used
Solr as the search engine, and have written custom backend classes to interact with it. The search backend class used
by Freesound is defined in settings.SEARCH_ENGINE_BACKEND_CLASS.

If a new search engine backend class is to be implemented, it must closely follow the API defined in the 
utils.search.SearchEngineBase docstrings. There is a Django management command that can be used in order to test
the implementation of a search backend. You can run it like:

    docker compose run --rm web python manage.py test_search_engine_backend -fsw --backend utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine

Please read carefully the documentation of the management command to better understand how it works and how is it
doing the testing.

### Freesound analysis pipeline

In February 2022 we released a refactoring of the analysis pipeline that allows us to more easily incorporate new audio 
analysis algorithms in Freesound and to schedule the analysis of the whole collection of sounds. The new analysis pipeline 
is currecntly working in parallell with the older analysis pipeline therefore it has not yet replaced it, but at some point 
it will completely replace it. In this section there is an explanation about how the new analysis pipeline works and how it 
should be setup for local development. 

First of all, a clarification about what "analysis" and "processing" mean in the context of Freesound:

* `processing`: sound files are *processed* to generate the mp3/ogg previews and the waveform/spectrogram
images. `processing` also extracts some information from the audio files (like duration, number of channels) which is used
to populate the database.

* `analysis`: sound files are *analyzed* to extract low/mid/high-level audio features which can be later used
for different Freesound features. 

Before the analysis refactoring, analysis consisted in running the [Freesound Essentia extractor](https://essentia.upf.edu), 
the extractor features were used to populate the similarity search index. The new analysis pipeline adds support for adding 
extra analyzers beside Essentia's extractor. The code for the different audio analyzers is no longer in the main Freesound
repository but here: https://github.com/mtg/freesound-audio-analyzers. In order to create an analyzer that is compatible with
Freesound, it needs to be created following the specification and instructions of that repository. As a sumamry, new analyzers
need to be dockerized and incorporate a Python script which implements a simple API for analyzing sounds. That script also
takes care of logging in the Freesound infrastructure.

The new analysis pipeline uses job queues based on Celery/RabbitMQ. There is one job queue for every available analyzer. The 
available analyzers are exposed as workers that can consume tasks from their queues (this is also done by the Python script
included in the analyzers). If several workers are instantiated for a single analyzer, then the queue for that analyzer will 
be consumed at a faster rate, but there'll still be only one queue per analyzer.

Analysis jobs can be manually triggered using the `analyze(analyzer_name)` method of Freesound `Sound` objects. When a job
is triggered, it will be added to the corresponding Celery/RabbitMQ queue, and a `SoundAnalysis` object will be created in the
database. That object will be used to store the state of the analysis job as well as the results when the job finishes. Only one
`SoundAnalysis` object can exist per pair of sound ID <> analyzer name. If an analysis job for an analyzer is triggered for a
sound that has already been analyzed with that analyzer, the already existing `SoundAnalysis` object will be updated.

When an analyzer finishes an analysis job, it is supposed to write the analsyis results into a file stored in a specific location
within `freesound-data`folder (this is explained in https://github.com/mtg/freesound-audio-analyzers). Also, when an analysis job 
is finished, the analyzer will trigger another Celery task called `process_analysis_results` which will collect the analysis results 
and update the corresponding `SoundAnalysis` object in the Freesound database to reflect that. If an analyzer failed to process a sound,
that will also be reflected in the `SoundAnalysis` object by setting a status of `Failed`. The analysis logs stored are accessible through the
`SoundAnalysis` object and will hopefully show deatils about the anlaysis errors. If the analyzer has defined
a `descriptors_map` property in `settings.ANALYZERS_CONFIGURATION[analyzer_name]`, then the mapping will be used to load some of the
analysis results from the analysis output file and store them directly in the Freesound database (the `SoundAnalysis` object has a
JSON field to store `analysis_data`). Analysis results stored in the database can be easily used for indexing sounds and filtering 
them with the search engine and the Freesound API (for a "how to" see implementation examples for analyzer `ac-extractor_v3`).

It is not advised to add more than a *few thousands* of jobs in the Celery/RabbitMQ queue (we've experienced problems with that although
we never furthe investigated). For this reason, if we want to, e.g. analyze the whole Freesound with a new analyzer, we won't simply
iterate over all sounds and call `analyze(new_analyzer_name)`. Instead, the new analysis pipeline adds a management command named
`orchestrate_analysis` (in the sounds app) which is run at every hour will handle the triggering of analysis jobs. The idea is that
we define which analyzers we want available in Freesound using `settings.ANALYZERS_CONFIGURATION`, and then `orchestrate_analysis` takes
care of continuously checking the current analysis status of all sounds, and triggering jobs for pairs of sound<>analyzer that are missing.
That command will also take care of re-sending analysis jobs that have failed (with a maximum number of re-trials) and also logging all this
information to that we can easily keep track of the whole analysis status.

The Freesound admin pages for `SoundAnalysis` objects have been configured to be useful for dealing with the analysis of sounds, checking 
analysis logs, filtering by state and even re-triggering analysis jobs.


#### Running new analysis pipeline in local development

The new analysis pipeline includes the use of external audio analyzers implemented in a code repository at 
https://github.com/mtg/freesound-audio-analyzers. The docker compose of the main Freesound repository has defined 
services for the external analyzers which depend on docker images having been previously built from the 
`freesound-audio-analyzers` repository. To build these images you simply need to checkout the code repository and run 
`make`. Once the images are built, Freesound can be run including the external analyzer services by of the docker compose 
file by running `docker compose --profile analyzers up`

The new analysis pipeline uses a job queue based on Celery/RabbitMQ. RabbitMQ console can be accessed at port `5673`
(e.g. `http://localhost:5673/rabbitmq-admin`) and using `guest` as both username and password. Also, accessing 
`http://localhost:8000/monitor` will show a summary of the state of different analysis job queues (as well as queues
for Freesound async tasks other than analysis).


### Considerations when updating Django version

#### Preparation

- Make sure that there are no outstanding deprecation warnings for the version of django that we are upgrading to.

      docker compose run --rm web python -Wd manage.py test

Check for warnings of the form `RemovedInDjango110Warning` (TODO: Make tests fail if a warning occurs)

- Check each item in the Django release notes to see if it affects code in Freesound. In the final pull request, list each item and if affects us, and a link to the commit if a change was made.

- For the 'remember password' form we had copied django code and modified it to accept an email or a username, changes in django code could break this part. Check if there are changes that could imply a modification on this form.

- Check if `django.contrib.auth.forms.PasswordResetForm` method's code has changed with respect to the previous version. If it has changed see how this should be ported to our custom version of the form in `accounts.forms.FsPasswordResetForm`.

#### Upgrade

If the upgrade requires a database migration for django models, indicate this in the pull request. Include an estimate 
of the time required to perform this migration by first running the migration on fs-test

#### Validation

After doing all the changes follow this list as a guideline to check if things are working fine:

- Upload new sound
- Moderate sound
- post comment on sound
- Download sound
- follow user
- search and filter sounds
- create new post on forum 
- search post on forum
- send message to user 
- check that cross-site embeds work
- ...
- Check that CORS headers are working, by using a javascript app


### New developer onboarding (for admins)

* Add to Github team
* Add to Slack channel
* Give access to Sentry/Graylog
