# Custom values for connecting to Mysql.
MYSQL_CONNECT = dict(host="localhost", user="freesound_web", passwd="bleep", db="freesound", use_unicode=False)
# Custom values for connecting to PostgreSQL.
POSTGRES_CONNECT="host='localhost' dbname='freesound' user='freesoundpg' password='bleep'"

import MySQLdb.cursors
# SSCursor does not cache the full result in memory.
DEFAULT_CURSORCLASS = MySQLdb.cursors.SSCursor

# Add new banned user here, no need to patch the code.
CUSTOM_BANNED_USERS = ()
