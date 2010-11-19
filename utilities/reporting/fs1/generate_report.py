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
    sql = "select count(*) from audio_file where FROM_date(dateAdded) < '{y}-{m}-{d}';"
    return execute_query(sql, dates)





if __name__ == '__main__':
    data = {}
    queries = [#('users_accum_monthly',      lambda: get_users_accum(MONTHS)),
               #('users_accum_weekly',       lambda: get_users_accum(WEEKS)),
               #('downloads_accum_monthly',  lambda: get_downloads_accum(MONTHS[0:4])),
               #('downloads_accum_weekly',   lambda: get_downloads_accum(WEEKS)),
               #('uploads_accum_monthly',    lambda: get_downloads_accum(MONTHS)),
               ('uploads_accum_weekly',     lambda: get_downloads_accum(WEEKS)),
              ]
    for name, func in queries:
        print 'Executing query: %s' % name
        data[name] = func()
        print '.'
    report_file = os.path.join(os.path.dirname(__file__), 'report_freesound1_%d%02d%02d.json' % (NOW.year, NOW.month, NOW.day))
    fp = file(report_file, 'w')
    json.dump(data, fp)
    fp.close()
    print "Generated report '%s' \t(date format: yyyymmdd)" % report_file
