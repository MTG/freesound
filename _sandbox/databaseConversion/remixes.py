#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'remixes' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from db_utils import get_sound_ids

OUT_FNAME = 'remixes.sql'

VALID_SOUND_IDS = get_sound_ids()


INSERT_ID = 0



def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """

    sound_id, parent_id = row
    
    if sound_id not in VALID_SOUND_IDS or parent_id not in VALID_SOUND_IDS:
        return

    INSERT_ID += 1

    fields = [INSERT_ID, sound_id, parent_id]
    return map(unicode, fields)



def migrate_table(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy sounds_sound_sources (id, from_sound_id, to_sound_id) 
        from stdin null as 'None';"""
    out.write(sql)

    query = """SELECT af1.ID, af1.parent 
        FROM audio_file af1 
        WHERE af1.parent is not null 
            and af1.parent != 0 
            and (select af2.ID from audio_file as af2 where af2.ID=af1.parent) 
                is not null ;"""
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row(row)
        if new_row:
            out.write(u"\t".join(new_row) + u"\n" )

    sql = """\.

    select setval('sounds_sound_sources_id_seq',(select max(id)+1 
        from sounds_sound_sources));
    vacuum analyze sounds_sound_sources;
    """
    out.write(sql)




def main():
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()

