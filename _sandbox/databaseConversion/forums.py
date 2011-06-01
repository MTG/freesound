#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'forums' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from django.template.defaultfilters import slugify
from text_utils import smart_character_decoding


OUT_FNAME = 'forums.sql'





def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """

    forum_id, forum_name, forum_desc, forum_order = row
    
    forum_name = smart_character_decoding(forum_name)
    forum_desc = smart_character_decoding(forum_desc)
    
    forum_name_slug = slugify(forum_name)
    
    fields = [forum_id, forum_order, forum_name, forum_name_slug, forum_desc, 
        0, None, 0]
    return map(unicode, fields)



def migrate_table(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy forum_forum (id, "order", name, name_slug, description, 
        num_threads, last_post_id, num_posts) from stdin null as 'None';
"""
    out.write(sql)

    query = """select forum_id, forum_name, forum_desc, forum_order 
        from phpbb_forums ;
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

    select setval('forum_forum_id_seq',(select max(id)+1 from forum_forum));
    vacuum analyze forum_forum;
    """
    out.write(sql)




def main():
    """Run the main code."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()

