#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'posts' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from db_utils import get_user_ids, get_thread_ids
from text_utils import prepare_for_insert, smart_character_decoding

OUT_FNAME = 'posts.sql'

CHECK_USER_IDS = True

if CHECK_USER_IDS:
    VALID_USER_IDS = get_user_ids()
    VALID_THREAD_IDS = get_thread_ids()


def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """

    post_id, topic_id, poster_id, post_time, post_text = row
    
    if (CHECK_USER_IDS and poster_id not in VALID_USER_IDS) \
            or (topic_id not in VALID_THREAD_IDS):
        return
    
    post_text = prepare_for_insert(smart_character_decoding(post_text))

    fields = [post_id, topic_id, poster_id, post_text, post_time, post_time]
    return map(unicode, fields)



def migrate_table(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """COPY forum_post (id, thread_id, author_id, body, created, 
        modified) FROM stdin null AS 'None';
"""
    out.write(sql)

    query = """SELECT p.post_id, p.topic_id, p.poster_id, 
        FROM_UNIXTIME(p.post_time), t.post_text 
        FROM phpbb_posts p INNER JOIN phpbb_posts_text t 
        ON p.post_id = t.post_id ;
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

    select setval('forum_post_id_seq',(select max(id)+1 from forum_post));
    vacuum analyze forum_post;
    """
    out.write(sql)




def main():
    """Run the main code."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()
