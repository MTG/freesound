import MySQLdb as my
import codecs, sys, re
from text_utils import prepare_for_insert

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False, use_unicode=False)
my_curs = my_conn.cursor()

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

        all_vars = [insert_id, id, parentID]
        
        insert_id += 1
        
        output_file.write(u"\t".join(map(unicode, all_vars)) + "\n")

print """
copy sounds_sound_sources (id, from_sound_id, to_sound_id) from '%s' null as 'None';
select setval('sounds_sound_sources_id_seq',(select max(id)+1 from sounds_sound_sources));
vacuum analyze sounds_sound_sources;
""" % output_filename