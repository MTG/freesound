#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'threads' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from db_utils import get_user_ids
from text_utils import prepare_for_insert, smart_character_decoding, \
        decode_htmlentities
import sys


OUT_FNAME = 'threads.sql'

CHECK_USER_IDS = True
if CHECK_USER_IDS:
    VALID_USER_IDS = get_user_ids()


VALID_FORUM_IDS = dict( (id, 0) for id in \
        [1, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14] )
SUNK = 0
REGULAR = 1
STICKY = 2


def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """

    topic_id, forum_id, topic_title, topic_poster, topic_time, \
        topic_status, topic_type = row
    
    if (CHECK_USER_IDS and topic_poster not in VALID_USER_IDS) \
            or (forum_id not in VALID_FORUM_IDS):
        return
    
    topic_title = decode_htmlentities(prepare_for_insert(
        smart_character_decoding(topic_title)))
    status = REGULAR
    
    if topic_status == 3: # moved
        print "don't know how to handle this..."
        sys.exit(1)
    if topic_type == 3: # post global announce
        print "don't know how to handle this..."
        sys.exit(1)

    if topic_status == 0: # unlocked
        status = REGULAR
    if topic_type == 0: # normal
        status = REGULAR
    
    if topic_type == 1: # sticky
        status = STICKY
    if topic_type == 2: # announce
        status = STICKY
        
    if topic_status == 1: # locked!
        status = SUNK

    fields = [topic_id, forum_id, topic_poster, topic_title, status, 0, 
        None, topic_time]
    
    return map(unicode, fields)



def migrate_table(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy forum_thread (id, forum_id, author_id, title, status, 
        num_posts, last_post_id, created) from stdin null as 'None';
"""
    out.write(sql)

    query = """select topic_id, forum_id, topic_title, topic_poster, 
        FROM_UNIXTIME(topic_time), topic_status, topic_type from phpbb_topics ;
"""
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row(row)
        if new_row:
            out.write(u"\t".join(new_row) + u"\n" )

    sql = """\.

    select setval('forum_thread_id_seq',(select max(id)+1 from forum_thread));
    vacuum analyze forum_thread;
    """
    out.write(sql)




def main():
    """Run the main code."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()

