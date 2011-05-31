#!/usr/bin/env python
# -*- coding: utf-8 -*-

from local_settings import *
import codecs
from db_utils import get_user_ids
from text_utils import smart_character_decoding

OUT_FNAME = 'packs.sql'
VALID_USER_IDS = get_user_ids()



def transform_row_packs(row):
    rowid, name, user_id, created = row
    
    if user_id not in VALID_USER_IDS:
        return 
    
    name = smart_character_decoding(name)
    
    description = ""
    is_dirty = "t"
    num_downloads = 0
    
    if rowid == 1420:
        user_id = 588695

    fields = [rowid, name, user_id, created, description, is_dirty, 
        num_downloads]
    return map(unicode, fields)



def migrate_packs(curs):
    
    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql_head = """copy sounds_pack (id, name, user_id, created, description, 
    is_dirty, num_downloads) from stdin;
"""
    out.write(sql_head)

    query = """SELECT ID, name, userID, date FROM audio_file_packs 
        WHERE (select audio_file.id from audio_file where 
        packID=audio_file_packs.id limit 1) is not null"""
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row_packs(row)
        if new_row:
            out.write(u"\t".join(new_row) + u"\n" )

    sql_tail = """\.

    select setval('sounds_pack_id_seq',(select max(id)+1 from sounds_pack));
    vacuum analyze sounds_pack;
"""
    out.write(sql_tail)



def main():
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_packs(curs)

if __name__ == '__main__':
    main()
