![Freesound](media/images/logo_bw.png)

This repository contains the source code of the [Freesound](https://freesound.org) website.

Freesound is a project by the [Music Technology Group](http://www.mtg.upf.edu) (MTG), [Universitat Pompeu Fabra](http://upf.edu) (UPF).

[![Build Status](https://travis-ci.org/MTG/freesound.svg?branch=master)](https://travis-ci.org/MTG/freesound)


## License

All the source code in this repository is licensed as GNU Affero. Some of the dependencies might have their own licenses. See the [_LICENSE](https://github.com/MTG/freesound/tree/master/_LICENSE) folder for more details.


## Authors

For a list of authors please check out the [contributors](https://github.com/MTG/freesound/graphs/contributors) page.


## Development

Freesound is composed by a numnber of different services which can be run and orchestrated using Docker . The main service is provided by the `web` container which runs the Freesound Django application. Check out [this blog post](https://opensource.creativecommons.org/blog/entries/freesound-intro/) for some information about the Freesound technology stack. If you're to do development for Freesound, please checkout the [DEVELOPERS](https://github.com/MTG/freesound/blob/master/DEVELOPERS.md) file for some guidelines. 

Below are instructions for setting up a local Freesound installation for development. It is assumed that you have a working Docker installation.


### Setting up Freesound for development in 13 easy steps

1. Clone source code repository

  ```
git clone git@github.com:MTG/freesound.git
cd freesound
```

2. Create a directorty named `freesound-data` inside the repository folder

  ```
mkdir freesound-data
```

3. Download the Freesound development data zip file (~20GB) and uncompress it inside `freesound-data`. You should request this file to Freesound admins. File structure should look like this:

  ```
freesound/
freesound/freesound-data/
freesound/freesound-data/analysis/
freesound/freesound-data/avatar/
...
```

4. Download Freesound development similarity index data and tag recommendation models and place them under `freesound-data/similarity_index/` and `freesound-data/tag_recommendation_models` directories respectively (you'll need to create the directories). You should request these files to Freesound admins.


5. Rename `freesound/local_settings.example.py` file so you can customise Django settings if needed and create a `.env` file with your local user UID

  ```
cp freesound/local_settings.example.py freesound/local_settings.py
echo FS_USER_ID_FROM_ENV=$(id -u) > .env
```

6. [Optional] Create API credentials for the 3rd party services listed below and add them to your own `freesound/local_settings.py` file (check `settings.py` to know the config parameter names that you need to fill in):
 * Mapbox
 * Recaptcha 


7. Build the base Freesound Docker image

  ```
make -C docker
```

8. Build all Docker containers. The first time you run this command can take a while as a number of Docker images need to be downloaded and things need to be installed and compiled. 

  ```
docker-compose build
```

9. Run the database container and load a development database dump. You should request the development database dump (~50MB) to Freesound admins.

  ```
docker-compose up -d db
cat /path/to/freesound/development/db/dump.sql | docker-compose run --rm db psql -h db -U freesound  -d freesound
```

10. Update database by running Django migrations

  ```
docker-compose run --rm web python manage.py migrate
```

11. Create a superuser account to be able to login to the local Freesound website and to the admin site
  ```
docker-compose run --rm web python manage.py createsuperuser
```

12. Run all services 🎉 

  ```
docker-compose up
```
  This might take significant time as many services will be started at once. When done, you should be able to point your browser to `http://localhost:8000` and see the Freesound website up and running!


13. Build the search index so you can, well, search

  ```
# Open a new terminal window so the services started in the previous step keep running
docker-compose run --rm web python manage.py reindex_solr
docker-compose run --rm web python manage.py reindex_solr_forum
```

After following the steps you'll have a fully functional Freesound installation up and running, including the search, sound similarity and audio processing features (and more!). As a sort of *bonus step*, you can run Django's shell plus command like that:

```
docker-compose run --rm web python manage.py shell_plus
```

Because the `web` container mounts a named volume for the home folder of the user running the shell plus process, command history should be kept between container runs :)

In most situations it is possible that not all Freesound services need to be running. You can selectively run services using the `docker-compose` interface and this will speed up the startup time. For example, the most common service you'll need for development will be the `web` container and (maybe) `search`. Then you can do:

```
docker-compose up web search
```


### Running tests

You can run tests using the Django test runner in the `web` container like that:

```
docker-compose run --rm web python manage.py test --setings=freesound.test_settings.py  accounts apiv2 bookmarks donations follow forum general geotags messages monitor ratings search sounds support tags tickets utils wiki
```

Note that Django app names need to be specified so we only run tests for the Freesound apps and not for 3rd parties.