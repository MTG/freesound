import MySQLdb as my
import psycopg2
import codecs
from local_settings import *

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
ppsql_cur = ppsql_conn.cursor()
print "getting all valid sound ids"
ppsql_cur.execute("SELECT id FROM sounds_sound")
valid_sound_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"

start = 0
granularity = 10000
insert_id = 0

while True:
    print start
    my_curs.execute("SELECT af1.ID, af1.parent FROM audio_file af1 WHERE af1.parent is not null and af1.parent != 0 and (select af2.ID from audio_file as af2 where af2.ID=af1.parent) is not null limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, parentID = row
        
        if id not in valid_sound_ids or parentID not in valid_sound_ids:
            continue

        all_vars = [insert_id, id, parentID]
        
        insert_id += 1
        
        output_file.write(u"\t".join(map(unicode, all_vars)) + "\n")

print """
copy sounds_sound_sources (id, from_sound_id, to_sound_id) from '%s' null as 'None';
select setval('sounds_sound_sources_id_seq',(select max(id)+1 from sounds_sound_sources));
vacuum analyze sounds_sound_sources;
""" % output_filename