from local_settings import *
import MySQLdb as my
import psycopg2
import codecs

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
ppsql_cur = ppsql_conn.cursor()
print "getting all valid sound ids"
ppsql_cur.execute("SELECT id FROM sounds_sound")
valid_sound_ids = set(row[0] for row in ppsql_cur.fetchall())
print "done"
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = set(row[0] for row in ppsql_cur.fetchall())
print "done"
print "getting all valid pack ids"
ppsql_cur.execute("SELECT id FROM sounds_pack")
valid_pack_ids = set(row[0] for row in ppsql_cur.fetchall())
print "done"

start = 0
granularity = 1000000

while True:
    print start

    my_curs.execute("select userID, audioFileID, packID, date from audio_file_downloads limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        userID, audioFileID, packID, date = row
        
        if userID not in valid_user_ids:
            continue

        if audioFileID and audioFileID not in valid_sound_ids:
            continue
        
        if packID and packID not in valid_pack_ids:
            continue
        
        output_file.write(u"\t".join(map(unicode, [userID, audioFileID, packID, date])) + "\n")

print """
DROP INDEX sounds_download_created;
DROP INDEX sounds_download_pack_id;
DROP INDEX sounds_download_sound_id;
DROP INDEX sounds_download_user_id;
ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_pkey;
ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_pack_id_fkey;
ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_sound_id_fkey;
ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_user_id_fkey;
ALTER TABLE sounds_download DROP CONSTRAINT sounds_download_user_id_key;
  
copy sounds_download (user_id, sound_id, pack_id, created) from '%s' null as 'None';

CREATE INDEX sounds_download_created ON sounds_download USING btree (created);
CREATE INDEX sounds_download_pack_id ON sounds_download USING btree (pack_id);
CREATE INDEX sounds_download_sound_id ON sounds_download USING btree (sound_id);
CREATE INDEX sounds_download_user_id ON sounds_download USING btree (user_id);
ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_pkey PRIMARY KEY (id);
ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_pack_id_fkey FOREIGN KEY (pack_id) REFERENCES sounds_pack (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_sound_id_fkey FOREIGN KEY (sound_id) REFERENCES sounds_sound (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user (id) MATCH SIMPLE ON UPDATE NO ACTION ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE sounds_download ADD CONSTRAINT sounds_download_user_id_key UNIQUE (user_id, sound_id, pack_id);

select setval('sounds_download_id_seq',(select max(id)+1 from sounds_download));
vacuum analyze sounds_download;

-- don't forget to execute the queries in nightingale_sql_setup.sql
-- don't forget to create the triggers in nightingale_sql_triggers.sql
""" % (output_filename)