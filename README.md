![Freesound](freesound/static/bw-frontend/public/logos/logo-text.svg)

This repository contains the source code of the [Freesound](https://freesound.org) website.

Freesound is a project by the [Music Technology Group](http://www.mtg.upf.edu) (MTG), [Universitat Pompeu Fabra](http://upf.edu) (UPF).

[![Build Status](https://github.com/MTG/freesound/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/MTG/freesound/actions/workflows/unit-tests.yml)


## License

All the source code in this repository is licensed under the GNU Affero General Public License v3.
Some dependencies might have their own licenses.
See the [ACKNOWLEDGMENTS](ACKNOWLEDGMENTS) file for more details.


## Authors

For a list of authors, please check out the [contributors](https://github.com/MTG/freesound/graphs/contributors) page.


## Development

Freesound is composed of a number of different services which can be run and orchestrated using Docker. The main service is provided by the `web` container which runs the Freesound Django application. Check out [this blog post](https://opensource.creativecommons.org/blog/entries/freesound-intro/) for some information about the Freesound technology stack. If you're going to do development on Freesound, please check the [DEVELOPERS](https://github.com/MTG/freesound/blob/master/DEVELOPERS.md) file for some guidelines.

Below are instructions for setting up a local Freesound installation for development. It is assumed that you have a working Docker installation. Note that these instructions have on been tested on Linux and macOS, but might not work on Windows.


### Setting up Freesound for development in 13 easy steps

1. Clone source code repository

       git clone git@github.com:MTG/freesound.git
       cd freesound

2. Create a directory named `freesound-data` inside the repository folder

       mkdir freesound-data

3. Download the [Freesound development data zip file](https://drive.google.com/file/d/19BMxEv7Hyl08hCG7qJkkgzw3F5-IOhC-/view?usp=share_link) (~7GB) and uncompress it inside `freesound-data`. File structure should look like this:

       freesound-data/
       freesound-data/avatars/
       freesound-data/displays/
       freesound-data/previews/
       freesound-data/analysis/

4. Download the [Freesound tag recommendation models](https://drive.google.com/file/d/1snaktMysCXdThWKkYuKWoGc_Hk2BElmz/view?usp=sharing) and place the contents under `freesound-data/tag_recommendation_models` directory (you'll need to create that directory).

5. Rename `freesound/local_settings.example.py` file, so you can customise Django settings if needed and create a `.env` file with your local user UID and other useful settings. These other settings include `COMPOSE_PROJECT_NAME` and `LOCAL_PORT_PREFIX` which can be used to allow parallel local installations running on the same machine (provided that these to variables are different in the local installations), and `FS_BIND_HOST` which you should set to `0.0.0.0` if you need to access your local Freesound services from a remote machine.

       cp freesound/local_settings.example.py freesound/local_settings.py
       echo FS_USER_ID=$(id -u) > .env
       echo COMPOSE_PROJECT_NAME=freesound >> .env
       echo LOCAL_PORT_PREFIX= >> .env
       echo FS_BIND_HOST= >> .env

6. [Optional] Create API credentials for the 3rd party services listed below and add them to your own `freesound/local_settings.py` file (check `settings.py` to know the config parameter names that you need to fill in):

   * Mapbox
   * Recaptcha

7. Build all Docker containers. The first time you run this command can take a while as a number of Docker images need to be downloaded and things need to be installed and compiled.

       docker compose build

8. Download the [Freesound development database dump](https://drive.google.com/file/d/1-s4fkEBVbC0rNmqkh5kHoJreHsdGnDoa/view?usp=sharing) (~7MB), uncompress it and place the resulting `freesound-small-dev-dump-2025-03.sql` in the `freesound-data/db_dev_dump/` directory. Then run the database container and load the data into it using the commands below. You should get permission to download this file from Freesound admins.

       docker compose up -d db
       docker compose run --rm db psql -h db -U freesound  -d freesound -f freesound-data/db_dev_dump/freesound-small-dev-dump-2025-03.sql
       # or if the above command does not work, try this one
       docker compose run --rm --no-TTY db psql -h db -U freesound -d freesound < freesound-data/db_dev_dump/freesound-small-dev-dump-2025-03.sql

If you a prompted for a password, use `localfreesoundpgpassword`, this is defined in the `docker-compose.yml` file.

9. Update database by running Django migrations

        docker compose run --rm web python manage.py migrate

10. Create a superuser account to be able to log in to the local Freesound website and to the admin site

        docker compose run --rm web python manage.py createsuperuser

11. Build static files (use this every time you edit a frontend file, or use the frontend profile: see next step)

        docker compose run --rm frontend_builder npm run build

12. Run services 🎉

        docker compose up

    When running this command, the most important services that make Freesound work will be run locally.
    This includes the web application and database, but also the search engine, cache manager, queue manager and asynchronous workers, including audio processing.
    You should be able to point your browser to `http://localhost:8000` and see the Freesound website up and running!

    If you are working on frontend assets (JS, CSS, SCSS), use the `frontend` profile to automatically rebuild on changes:

        docker compose --profile frontend up

13. Build the search index, so you can search for sounds and forum posts

        # Open a new terminal window so the services started in the previous step keep running
        docker compose run --rm web python manage.py reindex_search_engine_sounds
        docker compose run --rm web python manage.py reindex_search_engine_forum

    After following the steps, you'll have a functional Freesound installation up and running, with the most relevant services properly configured.
    You can run Django's shell plus command like this:

        docker compose run --rm web python manage.py shell_plus

    Because the `web` container mounts a named volume for the home folder of the user running the shell plus process, command history should be kept between container runs :)

14. (extra) Load audio descriptors and similarity vectors to the database and reindex the search index. This is necessary to make audio descriptors available thorugh the API and to make similarity search work. Note that for this to work, you need to have properly set the development data folder, and you should see some files inside the `freesound-data/analysis` folders which store the (previously computed) results of Freesound audio analysers.

        # First run the following command which will create relevant objects in the DB. Note that this can take some minutes.
        docker compose run --rm web python manage.py create_consolidated_sound_analysis_and_sim_vectors --force

        # Then re-create the search engine sounds index after audio descriptors data has been loaded in the DB. You need to specifically indicate that similarity vectors should be added.
        docker compose run --rm web python manage.py reindex_search_engine_sounds --include-similarity-vectors


The steps above will get Freesound running, but to save resources in your local machine some non-essential services will not be started by default. If you look at the `docker-compose.yml` file, you'll see that some services are marked with the profile `analyzers` or `all`. These services include sound tag recommendation and the audio analyzers. To run these services you need to explicitly tell `docker compose` using the `--profile` (note that some services need additional configuration steps (see *Freesound analysis pipeline* section in `DEVELOPERS.md`):

        docker compose --profile analyzers up   # To run all basic services + sound analyzers
        docker compose --profile all up         # To run all services


### Running tests

You can run tests using the Django test runner in the `web` container like that:

    docker compose run --rm web pytest
