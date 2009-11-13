from local_settings import *
import MySQLdb as my
import codecs
import psycopg2

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

start = 0
granularity = 100000

content_type_id = 19

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

while True:
    print start
    
    my_curs.execute("""SELECT afc.ID, afc.audioFileID, afc.userID, afc.vote, afc.date FROM audio_file_vote AS afc LIMIT %d, %d""" % (start, granularity))

    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, object_id, user_id, rating, created = row

        if object_id not in valid_sound_ids or user_id not in valid_user_ids:
            continue
        
        output_file.write(u"\t".join(map(unicode, [id, user_id, rating, content_type_id, object_id, created])) + "\n")

print """
copy ratings_rating (id, user_id, rating, content_type_id, object_id, created) from '%s';
select setval('ratings_rating_id_seq',(select max(id)+1 from ratings_rating));
vacuum analyze ratings_rating;
""" % output_filename