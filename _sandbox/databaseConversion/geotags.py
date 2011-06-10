#!/usr/bin/env python
# -*- coding: utf-8 -*-

from local_settings import *
import codecs
from db_utils import get_user_ids, get_sound_ids

OUT_FNAME = 'geotags.sql'

VALID_USER_IDS = get_user_ids()
VALID_SOUND_IDS = get_sound_ids()

# We must run all the 'update sounds_sound' commands at the end.
# Put them in this list and print it at the end.
UPDATE_SOUNDS = [] 


def transform_row(row):
    global UPDATE_SOUNDS

    myid, user_id, object_id, lon, lat, zoom, created = row

    if (object_id not in VALID_SOUND_IDS) or \
        (user_id not in VALID_USER_IDS):
        return
    
    # This must be run at the end of the sql file.
    sql = "update sounds_sound set geotag_id=%d where id=%d;" \
        % (myid, object_id)
    UPDATE_SOUNDS.append(sql)

    return map(unicode, [myid, user_id, lon, lat, int(zoom), created]) 



def migrate_geotags(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy geotags_geotag (id, user_id, lon, lat, zoom, created) 
        from stdin;
"""
    out.write(sql)

    query = """SELECT
            geotags.id, userID, audioFileID, lon, lat, zoom, date
        FROM geotags
        LEFT JOIN audio_file on audio_file.id=geotags.audioFileID
        LEFT JOIN phpbb_users on phpbb_users.user_id=audio_file.userID
        WHERE
            audio_file.id is not null and
            phpbb_users.user_id is not null"""
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row(row)
        if new_row:
            out.write(u"\t".join(new_row) + u"\n" )

    sql = """\.

    select setval('geotags_geotag_id_seq',
        (select max(id)+1 from geotags_geotag));
    vacuum analyze geotags_geotag;
    """
    out.write(sql)

    out.write(u"\n".join(UPDATE_SOUNDS))
    out.write("vacuum analyze sounds_sound;""")



def main():
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_geotags(curs)

if __name__ == '__main__':
    main()
