import MySQLdb as my
import psycopg2
import codecs
from local_settings import *

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

output_filename2 = '/tmp/importfile2.dat'
output_file2 = codecs.open(output_filename2, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
ppsql_cur = ppsql_conn.cursor()
print "getting all valid sound ids"
ppsql_cur.execute("SELECT id FROM sounds_sound")
valid_sound_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"


start = 0
granularity = 1000

while True:
    print start
    my_curs.execute("""
    SELECT
        geotags.id, userID, audioFileID, lon, lat, zoom, date
    FROM geotags
    LEFT JOIN audio_file on audio_file.id=geotags.audioFileID
    LEFT JOIN phpbb_users on phpbb_users.user_id=audio_file.userID
    WHERE
        audio_file.id is not null and
        phpbb_users.user_id is not null
    limit %d, %d""" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, user_id, object_id, lon, lat, zoom, created = row
        
        if (object_id not in valid_sound_ids) or (user_id not in valid_user_ids):
            continue
        
        zoom = int(zoom)
        
        output_file.write(u"\t".join(map(unicode, [id, user_id, lon, lat, zoom, created])) + "\n")
        output_file2.write("update sounds_sound set geotag_id=%d where id=%d;\n" % (id, object_id))

print """
copy geotags_geotag (id, user_id, lon, lat, zoom, created) from '%s';
select setval('geotags_geotag_id_seq',(select max(id)+1 from geotags_geotag));
vacuum analyze geotags_geotag;
-- NOW RUN COMMAND: psql freesound < %s
vacuum analyze sounds_sound;
""" % (output_filename, output_filename2)