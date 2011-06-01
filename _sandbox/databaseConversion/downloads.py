#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate 'downloads' from Freesound1 to Freesound2.
"""

from local_settings import *
import codecs
from db_utils import get_user_ids, get_sound_ids, get_pack_ids

OUT_FNAME = 'downloads.sql'

VALID_USER_IDS = get_user_ids()
VALID_SOUND_IDS = get_sound_ids()
VALID_PACK_IDS = get_pack_ids()



def transform_row(row):
    """Get a row (sequence), transform the values, return a sequence.

    Returns None if the row shouldn't be migrated.
    """
    userID, audioFileID, packID, date = row
    
    if userID not in VALID_USER_IDS:
        return
    if audioFileID and audioFileID not in VALID_SOUND_IDS:
        return
    if packID and packID not in VALID_PACK_IDS:
        return
    
    fields = [userID, audioFileID, packID, date]
    return map(unicode, fields)



def migrate_table(curs):
    """Generates SQL sentences for migrating the table. Output to file.
    """

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """
    DROP INDEX sounds_download_created;
    DROP INDEX sounds_download_pack_id;
    DROP INDEX sounds_download_sound_id;
    DROP INDEX sounds_download_user_id;
    ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_pkey;
    ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_pack_id_fkey;
    ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_sound_id_fkey;
    ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_user_id_fkey;
    ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_user_id_key;
      
    copy sounds_download (user_id, sound_id, pack_id, created) 
        from stdin null as 'None';
"""
    out.write(sql)

    query = """select userID, audioFileID, packID, date 
        from audio_file_downloads ;"""
    curs.execute(query)

    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row(row)
        if new_row:
            out.write(u"\t".join(new_row) + u"\n" )

    sql = """\.

    CREATE INDEX sounds_download_created ON sounds_download 
        USING btree (created);
    CREATE INDEX sounds_download_pack_id ON sounds_download 
        USING btree (pack_id);
    CREATE INDEX sounds_download_sound_id ON sounds_download 
        USING btree (sound_id);
    CREATE INDEX sounds_download_user_id ON sounds_download 
        USING btree (user_id);
    ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_pkey 
        PRIMARY KEY (id);
    ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_pack_id_fkey 
        FOREIGN KEY (pack_id) REFERENCES sounds_pack (id) 
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE 
            INITIALLY DEFERRED;
    ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_sound_id_fkey 
        FOREIGN KEY (sound_id) REFERENCES sounds_sound (id) 
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE 
        INITIALLY DEFERRED;
    ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES auth_user (id) 
        MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE 
        INITIALLY DEFERRED;
    ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_user_id_key 
        UNIQUE (user_id, sound_id, pack_id);

    select setval('sounds_download_id_seq',(select max(id)+1 
        from sounds_download));
    vacuum analyze sounds_download;

    -- don't forget to execute the queries in nightingale_sql_setup.sql
    -- don't forget to create the triggers in nightingale_sql_triggers.sql
    """
    out.write(sql)




def main():
    """Run the main code."""
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_table(curs)

if __name__ == '__main__':
    main()

