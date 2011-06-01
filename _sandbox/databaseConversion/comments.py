#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'comments' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from HTMLParser import HTMLParseError
from text_utils import prepare_for_insert, smart_character_decoding
from db_utils import get_user_ids, get_sound_ids, get_content_id

OUT_FNAME = 'comments.sql'

VALID_USER_IDS = get_user_ids()
VALID_SOUND_IDS = get_sound_ids()
CONTENT_TYPE_ID = get_content_id('sounds', 'sound')



def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """

    row_id, object_id, user_id, created, comment = row
    
    if object_id not in VALID_SOUND_IDS or user_id not in VALID_USER_IDS:
        return
    
    try:
        comment = prepare_for_insert(smart_character_decoding(comment))
    except HTMLParseError:
        print comment
        return

    fields = [row_id, user_id, CONTENT_TYPE_ID, object_id, comment, 
            None, created]
    return map(unicode, fields)



def migrate_table(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy comments_comment (id, user_id, content_type_id, object_id,
        comment, parent_id, created) from stdin null as 'None';
"""
    out.write(sql)

    query = """
    SELECT afc.ID, afc.audioFileID, afc.userID, afc.date, afc.text FROM audio_file_comments AS afc
    LEFT JOIN audio_file AS af ON af.id=afc.audioFileID
    LEFT JOIN phpbb_users AS u ON u.user_id=afc.userID
    WHERE
    af.id IS NOT NULL AND
    u.user_id IS NOT NULL
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

    select setval('comments_comment_id_seq', (select max(id)+1 
        from comments_comment));
    vacuum analyze comments_comment;
    """
    out.write(sql)




def main():
    """Run the main code."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()

