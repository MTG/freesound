import MySQLdb as my
import psycopg2
import codecs, sys
from text_utils import slugify
from text_utils import prepare_for_insert, smart_character_decoding
from local_settings import *

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
ppsql_cur = ppsql_conn.cursor()
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"

start = 0
granularity = 1000

while True:
    print start
    my_curs.execute("SELECT ID, name, userID, date FROM audio_file_packs WHERE (select audio_file.id from audio_file where packID=audio_file_packs.id limit 1) is not null limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    cleaned_data = []
    for row in rows:
        id, name, user_id, created = row
        
        if user_id not in valid_user_ids:
            continue
        
        name = smart_character_decoding(name)
        
        description = ""
        name_slug = slugify(name)
        
        if id == 1420:
            user_id = 588695;
        
        output_file.write(u"\t".join(map(unicode, [id, name, user_id, created, description, name_slug, 0])) + "\n")

print """
copy sounds_pack (id, name, user_id, created, description, name_slug, num_downloads) from '%s';
select setval('sounds_pack_id_seq',(select max(id)+1 from sounds_pack));
vacuum analyze sounds_pack;
""" % output_filename