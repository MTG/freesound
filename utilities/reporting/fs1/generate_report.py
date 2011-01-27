#!/usr/bin/env python

from settings import *
import MySQLdb, os, sys
import mx.DateTime as dt
import simplejson as json



db=MySQLdb.connect(user=DB_USER, passwd=DB_PASS, db=DB_NAME)
cursor = db.cursor()
cursor2 = db.cursor()

FIRST_YEAR = 2005
FIRST_MONTH = 5

NOW  = dt.now()
THEN = dt.DateTime(2005, 4, 1)


def generate_dates(start, end, delta_months, delta_days):
    d = start
    while d < end:
        yield d
        d = d + dt.RelativeDateTime(days=delta_days, months=delta_months)


MONTHS = [x for x in generate_dates(THEN, NOW, 1, 0)]
WEEKS  = [x for x in generate_dates(THEN, NOW, 0, 7)]
DAYS   = [x for x in generate_dates(THEN, NOW, 0, 1)]


def execute_query(query, dates):
    '''
    `query` should include {y}, {m}, and {d} format directives for year, month, and day respectively.
    '''
    counts = []
    for d in dates:
        sys.stdout.write('.')
        sys.stdout.flush()
        sql = query.format(y=d.year, m=d.month, d=d.day)
        cursor.execute(sql)
        result = cursor.fetchone()
        counts.append(result[0])
    return counts


def get_users_accum(dates):
    sql = "select count(*) from phpbb_users where FROM_UNIXTIME(user_regdate) < '{y}-{m}-{d}';"
    return execute_query(sql, dates)

def get_downloads_accum(dates):
    sql = "select count(*) from audio_file_downloads where date(date) < '{y}-{m}-{d}';"
    return execute_query(sql, dates)

def get_uploads_accum(dates):
    sql = "select count(*) from audio_file where date(dateAdded) < '{y}-{m}-{d}';"
    return execute_query(sql, dates)





if __name__ == '__main__':

    queries = {'users_accum':
               "select count(*) from phpbb_users where FROM_UNIXTIME(user_regdate) < '{y}-{m}-{d}';",
               'downloads_monthly':
               "select count(*) from audio_file_downloads where year(date) = {y} AND month(date) = {m};",
               'downloads_daily':
               "select count(*) from audio_file_downloads where date(date) = '{y}-{m}-{d}';",
               'uploads_monthly':
               "select count(*) from audio_file where year(dateAdded) = {y} AND month(dateAdded) = {m};",
               'uploads_daily':
               "select count(*) from audio_file where date(dateAdded) = '{y}-{m}-{d}';",
               }

    data = {}
    execs    = [('users_accum_monthly', # will be the index in the json result file
                'users_accum',         # will be used to look up the sql query
                MONTHS),               # will be used as input for the dates

               ('users_accum_weekly',
                'users_accum',
                WEEKS),

               ('downloads_monthly',
                'downloads_monthly',
                MONTHS),

               ('downloads_daily',
                'downloads_daily',
                DAYS),

               ('uploads_monthly',
                'uploads_monthly',
                DAYS),

               ('uploads_daily',
                'uploads_daily',
                DAYS),
              ]
    for result_name, query_name, dates in execs:
        print 'Executing query: %s' % result_name
        data[result_name] = execute_query(queries[query_name], dates)
        print '.'
    report_file = os.path.join(os.path.dirname(__file__), 'report_freesound1_%d%02d%02d_to_%d%02d%02d.json' \
                               % (THEN.year, THEN.month, THEN.day, NOW.year, NOW.month, NOW.day))
    fp = file(report_file, 'w')
    json.dump(data, fp)
    fp.close()
    print "Generated report '%s' \t(date format: yyyymmdd)" % report_file
