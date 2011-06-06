#!/usr/bin/env python
# -*- coding: utf-8 -*-

from local_settings import *
import codecs
from db_utils import get_user_ids
from text_utils import prepare_for_insert, smart_character_decoding

OUT_FNAME = 'sounds.sql'
VALID_USER_IDS = get_user_ids()
MISSING_FILES = [49525, 57342, 57343, 57346, 57355]

MD5S = {}


def transform_row(row, curs_description):

    myid, original_filename, user_id, duration, bitrate, bitdepth, filesize, \
        created, samplerate, channels, pack_id, moderation_state, \
        moderation_bad_description, md5, base_filename_slug, mytype = row

    if user_id not in VALID_USER_IDS:
        return
    if myid in MISSING_FILES:
        return

    if md5 in MD5S:
        return
    else:
        MD5S[md5] = 1

    original_filename = smart_character_decoding(original_filename)

    query = """SELECT text FROM audio_file_text_description 
        where audioFileId = %d"""
    curs_description.execute(query, (myid,) )

    descriptions = []
    for d in curs_description.fetchall():
        descriptions.append(smart_character_decoding(d[0]))

    description = prepare_for_insert( u"\n".join(descriptions))

    original_path = None
    moderation_date = created
    processing_date = created
    similarity_state = "PE"
    processing_state = "PE"
    license_id = 1
    processing_log = None

    mytype = mytype.lower()

    if moderation_state in [0, 3]:
        moderation_state = "PE"
    elif moderation_state == 1:
        moderation_state = "OK"
    elif moderation_state in [2, 4]:
        moderation_state = "DE"

    moderation_bad_description = "f" if moderation_bad_description == 0 else "t"

    geotag = None
    num_comments = 0
    num_downloads = 0
    avg_rating = 0
    num_ratings = 0
    moderation_note = None

    all_vars = [myid,
        user_id,
        created,
        original_path,
        base_filename_slug,
        description,
        license_id,
        original_filename,
        pack_id,
        mytype,
        duration,
        bitrate,
        bitdepth,
        samplerate,
        filesize,
        channels,
        md5,
        moderation_state,
        moderation_date,
        moderation_note,
        moderation_bad_description,
        processing_state,
        processing_date,
        processing_log,
        geotag,
        num_comments,
        num_downloads,
        avg_rating,
        num_ratings,
        similarity_state]

    return map(unicode, all_vars)




def migrate_sounds(curs, curs_description):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy sounds_sound (id, user_id, created, original_path,
    base_filename_slug, description, license_id, original_filename, pack_id,
    type, duration, bitrate, bitdepth, samplerate, filesize, channels, md5,
    moderation_state, moderation_date, moderation_note, has_bad_description,
    processing_state, processing_date, processing_log, geotag_id, num_comments,
    num_downloads, avg_rating, num_ratings, similarity_state) from stdin null
    as 'None';
    """
    out.write(sql)

    query = """SELECT ID, originalFilename, userID, duration, bitrate, 
        bitdepth, filesize, dateAdded, samplerate, channels, packID, 
        moderated, badDescription, md5, newFilename, extension 
        FROM audio_file ORDER BY dateAdded"""
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row(row, curs_description)
        if new_row:
            out.write(u"\t".join(new_row) + u"\n" )

    sql = """\.

    select setval('sounds_sound_id_seq',(select max(id)+1 from sounds_sound));
    update sounds_sound set original_path = '/mnt/freesound-data/' || id/1000 || '/sounds/' || base_filename_slug || '.' || type;
    vacuum analyze sounds_sound;
    """
    out.write(sql)



def main():
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    # We use two descriptors because two queries will run at the same time.
    # SSCursor class breaks if a new query is sent before all responses 
    # have been fetched.
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    curs_description = conn.cursor()

    migrate_sounds(curs, curs_description)


if __name__ == '__main__':
    main()
