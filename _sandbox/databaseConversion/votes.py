#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'votes' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from db_utils import get_user_ids, get_sound_ids, get_content_id

OUT_FNAME = 'votes.sql'

VALID_USER_IDS = get_user_ids()
VALID_SOUND_IDS = get_sound_ids()
CONTENT_TYPE_ID = get_content_id('sounds', 'sound')


def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """

    row_id, object_id, user_id, rating, created = row

    if object_id not in VALID_SOUND_IDS or user_id not in VALID_USER_IDS:
        return
        
    fields = [row_id, user_id, rating, CONTENT_TYPE_ID, object_id, created]
    return map(unicode, fields)



def migrate_table(curs):
    """Generates SQL sentences for migrating the table. Output to file.
    """

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy ratings_rating (id, user_id, rating, content_type_id, 
        object_id, created) from stdin ;
"""
    out.write(sql)

    query = """SELECT afc.ID, afc.audioFileID, afc.userID, afc.vote, afc.date 
    FROM audio_file_vote AS afc ;
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

    select setval('ratings_rating_id_seq',(select max(id)+1 
        from ratings_rating));
    vacuum analyze ratings_rating;
    """
    out.write(sql)




def main():
    """Run the main code."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()

