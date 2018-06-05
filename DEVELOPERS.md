# Freesound Development notes


## Creating a small, anonymised database for development

For development purposes, we want a copy of the database which is
representative of the database but does not contain any personal
information and is smaller than the main database.

We do this by making a copy of the database, running a command
which randomly removes most of the users and their associated data

1. Make a dump
2. Configure Freesound to point to this database (`local_settings.py`)
3. Run the prune command:

        python manage.py prune_database
4. Fix summary counts in the database (number of sounds, comments, downloads, etc)

        python manage.py report_count_statuses
5. Anonymise personal information in the database. Use the script `db_anonymize` from
   the `freesound-scripts` repository
