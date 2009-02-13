import MySQLdb as my
import codecs
import sys

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

output_filename2 = '/tmp/importfile2.dat'
output_file2 = codecs.open(output_filename2, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False)
my_curs = my_conn.cursor()

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