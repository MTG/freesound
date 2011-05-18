1. Create a postgresql db with syncdb

    * Don't create a super user!

2. Run scripts in the following order

    * users
    * profile
    * packs
    * sounds
    * tags
    * geotags
    * messages
    * remixes
    * forums
    * threads
    * posts
    * comments
    * votes
    * downloads

3. Run _sql/nightinggale_* scripts

    * First: nightingale_sql_setup.sql
    * Second: nightingale_triggers.sql

4. Run script to determine where to start processing again.

    * The script is a Django command called 'post_conversion.py'

5. Run script to do pending processing

    * Call the django command gm_client_processing with the --pending option!

