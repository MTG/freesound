import MySQLdb, MySQLdb.cursors
import psycopg2
from local_settings import MYSQL_CONNECT, POSTGRES_CONNECT

def query_to_dict(query):
    """Runs a Postgresql query, returns a dict.

    Returns a dictionary.
    """
    ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
    ppsql_cur = ppsql_conn.cursor()
    ppsql_cur.execute(query)
    return dict((row[0], 1) for row in ppsql_cur.fetchall())


def get_user_ids():
    """Gets all valid user ids from Postgresql. Returns a dictionary."""
    return query_to_dict("SELECT id FROM auth_user")


def get_sound_ids():
    """Gets all valid sound ids from Postgresql. Returns a dictionary."""
    return query_to_dict("SELECT id FROM sounds_sound")


def get_thread_ids():
    """Gets all valid thread ids from Postgresql. Returns a dictionary."""
    return query_to_dict("SELECT id FROM forum_thread")


def get_pack_ids():
    """Gets all valid thread ids from Postgresql. Returns a dictionary."""
    return query_to_dict("SELECT id FROM sounds_pack")



def get_content_id(app, model):
    """Gets content type from Postgresql, for given app/model. 
    
    Returns a dictionary."""
    ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
    ppsql_cur = ppsql_conn.cursor()
    query = "select id from django_content_type where app_label='%s' and model='%s'"
    ppsql_cur.execute(query % (app, model))
    return ppsql_cur.fetchall()[0][0]



def get_mysql_cursor():
    """Connect to Mysql, return a cursor."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    # SSCursor does not cache the full result in memory.
    return conn.cursor(MySQLdb.cursors.SSCursor)


def queryrunner(curs, query, call_transform):
    """Run the 'query' and callback 'call_transform' function for
    every row.
    """
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        print u"\t".join(call_transform(row))

