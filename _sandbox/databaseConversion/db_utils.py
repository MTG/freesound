import MySQLdb, MySQLdb.cursors
import psycopg2
from local_settings import MYSQL_CONNECT, POSTGRES_CONNECT


def get_user_ids():
    """Gets all valid user ids from Postgresql.

    Returns a dictionary.
    """
    ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
    ppsql_cur = ppsql_conn.cursor()
    ppsql_cur.execute("SELECT id FROM auth_user")
    return dict((row[0], 1) for row in ppsql_cur.fetchall())


def get_sound_ids():
    """Gets all valid sound ids from Postgresql.

    Returns a dictionary.
    """
    ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
    ppsql_cur = ppsql_conn.cursor()
    ppsql_cur.execute("SELECT id FROM sounds_sound")
    return dict((row[0], 1) for row in ppsql_cur.fetchall())


def get_content_id(app, model):
    ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
    ppsql_cur = ppsql_conn.cursor()
    ppsql_cur.execute("select id from django_content_type where app_label='%s' and model='%s'", (app, model))
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

