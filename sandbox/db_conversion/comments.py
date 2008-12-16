import MySQLdb as my
import codecs, sys
from django.template.defaultfilters import slugify
from text_utils import prepare_for_insert, smart_character_decoding

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False)
my_curs = my_conn.cursor()

start = 0
granularity = 1000

content_type_id = 18

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
        
        comment = prepare_for_insert(smart_character_decoding(comment))

        output_file.write(u"\t".join(map(unicode, [id, user_id, content_type_id, object_id, comment, None, created])) + "\n")

print """
copy comments_comment (id, user_id, content_type_id, object_id, comment, parent_id, created) from '%s' null as 'None';
select setval('comments_comment_id_seq', (select max(id)+1 from comments_comment));
vacuum analyze comments_comment;
""" % output_filename