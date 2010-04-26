Installation manual for Nightingale/Freesound
=============================================

This document describes the installation of Freesound in a Debian Lenny host.
Some configuration files may reside on different places for other distributions.

We chose to deploy freesound inside a virtualenv. This is optional but makes
easier to meet the Python requirements without creating conflicts with other
software.

Some prerequisites for local debugging/development:

 * python >= 2.5
 * postgresql up and running



Optional: work in a virtualenv
------------------------------

Install host-wide:

    $ sudo pip install virtualenv virtualenvwrapper

Create a virtualenv and work on it.

    $ mkvirtualenv freesound
    $ easy_install pip


Install Debian packages
-----------------------

Some Debian packages are need. Some could be installed with 'pip' in your
virtualenv but have non-Python dependencies or are hard to compile.

    $ sudo apt-get install sndfile-programs libsndfile1-dev \
        mplayer lame memcached vorbis-tools flac \
        python-psycopg2 ipython python-imaging python-dev \
        python-numpy

`libsndfile1-dev` is a requirement of the `scikit.audiolab` Python package.


Install Python packages
-----------------------

Download Freesound:

    $ git clone git://github.com/bram/freesound.git

Install required Python packages:

    $ pip install -r freesound/freesound/docs/requirements-python.txt



Optional: install pydev and eclipse
-----------------------------------

This is only recommended for local development.

 * Download the Platform Runtime Binary for eclipse. This is the most minimal
   configuration.
 * From within eclipse using software updates > install :
 * Install pydev and then configure the python interpreter
   (prefs > pydev > interpreter )
 * Install Eclipse Java Development Tools (JDT)
 * Download and install http://www.eclipse.org/gef/
 * Download and install Amateras Eclipse HTML Editor Plugin
 * Import the freesound project (import existing project into workspace)


Configuration
=============


Create a database
-----------------

(Note: replace <freesound_db> and <freesound_db_user> with the value you will
really use).

All database commands must be run by the user 'postgres', so

    # sudo su postgres

Create the freesound user.

    $ createuser -SDR -P <freesound_db_user>
	Enter password for new role:
	Enter it again:

Create a database.

    $ createdb --owner <freesound_db_user> --encoding=UTF-8 <freesound_db>

If your webserver is on another machine you must allow access to the database.
Edit your `/etc/postgresql/8.3/main/pg_hba.conf` and add something like:

    host    <freesound_db>  <freesound_db_user>  193.145.55.3/32   md5

Create the language plpgsql in the database

    createlang -d freesound plpgsql

Install the SQL triggers in the database:

	freesound/sql/nightingale_triggers.sql

If an import was done, run the initial setup which fixes the num_counts

	freesound/sql/nightingale_sql_setup.sql

Create a directory for logs
---------------------------

    $ sudo mkdir /var/log/freesound
    $ sudo chown <local_user>: /var/log/freesound


Create your local settings
--------------------------

Copy and edit as needed:

    cp local_settings.example.py local_settings.py

**Try it!**

cd to your nightingale directory and run: 

    %  python manage.py runserver

Open http://127.0.0.1:8000/ on your browser