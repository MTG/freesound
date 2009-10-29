Installation manual for Nightingale/Freesound
=============================================

prerequisites for local debugging/development:

 * python >= 2.5
 * postgresql up and running


For development you may want configure postgresql to use password authentication,
in pg_hba.sql:

    local all all trust
    host all all 127.0.0.1/32 trust

 * [django from trunk][django-trunk]
 * [psycopg2][psycopg2]

[django-trunk]: http://www.djangoproject.com/documentation/install/#installing-the-development-version
[psycopg2]: http://www.initd.org/tracker/psycopg/wiki/PsycopgTwo

(on linux distros you may find a ready made package for psycopg2)


Steps to install pydev and eclipse
==================================

 * download the Platform Runtime Binary for eclipse. this is the most minimal
   configuration.
 * from within eclipse using software updates > install :
 * install pydev and then configure the python interpreter
   (prefs > pydev > interpreter )
 * install Eclipse Java Development Tools (JDT)
 * download and install http://www.eclipse.org/gef/
 * download and install Amateras Eclipse HTML Editor Plugin
 * import the freesound project (import existing poject into workspace)


Database for freesound
======================

create the freesound user

    % sudo -u postgres createuser -P -e freesound
	Enter password for new role:
	Enter it again:
	Shall the new role be a superuser? (y/n) n
	Shall the new role be allowed to create databases? (y/n) n
	Shall the new role be allowed to create more new roles? (y/n) n

create a database

    % /usr/local/bin/createdb --owner freesound --encoding=UTF-8 freesound


Create your local settings
==========================

Copy the local_settings.example.py file to a local_settings.py file and edit to
suit your needs.

**Try it!**

cd to your nightingale directory and run: 

    %  python manage.py runserver

Open http://127.0.0.1:8000/ on your browser
