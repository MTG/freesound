from HTMLParser import HTMLParseError
from local_settings import *
from text_utils import prepare_for_insert, smart_character_decoding
import MySQLdb as my
import codecs
import psycopg2

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
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"
print "getting correct content_id"
ppsql_cur.execute("select id from django_content_type where app_label='sounds' and model='sound'")
content_type_id = ppsql_cur.fetchall()[0][0]
print "done"

start = 0
granularity = 1000

while True:
    print start
    my_curs.execute("""
    SELECT afc.ID, afc.audioFileID, afc.userID, afc.date, afc.text FROM audio_file_comments AS afc
    LEFT JOIN audio_file AS af ON af.id=afc.audioFileID
    LEFT JOIN phpbb_users AS u ON u.user_id=afc.userID
    WHERE
    af.id IS NOT NULL AND
    u.user_id IS NOT NULL
    limit %d, %d""" % (start, granularity))

    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, object_id, user_id, created, comment = row
        
        if object_id not in valid_sound_ids or user_id not in valid_user_ids:
            continue
        
        try:
            comment = prepare_for_insert(smart_character_decoding(comment))
        except HTMLParseError:
            print comment
            continue

        output_file.write(u"\t".join(map(unicode, [id, user_id, content_type_id, object_id, comment, None, created])) + "\n")

print """
copy comments_comment (id, user_id, content_type_id, object_id, comment, parent_id, created) from '%s' null as 'None';
select setval('comments_comment_id_seq', (select max(id)+1 from comments_comment));
vacuum analyze comments_comment;
""" % output_filename