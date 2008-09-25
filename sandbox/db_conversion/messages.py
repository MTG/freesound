import MySQLdb as my
import codecs
import sys

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

output_filename2 = '/tmp/importfile2.dat'
output_file2 = codecs.open(output_filename2, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=True)
my_curs = my_conn.cursor()

content_type_id = 18

start = 0
granularity = 1000

"""
class MessageBody(models.Model):
    body = models.TextField()

class Message(models.Model):
    user_from = models.ForeignKey(User, related_name='messages_sent')
    user_to = models.ForeignKey(User, related_name='messages_received')
    
    subject = models.CharField(max_length=128)
    
    body = models.ForeignKey(MessageBody)
        
    is_sent = models.BooleanField(default=True, db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    
    created = models.DateTimeField(db_index=True, auto_now_add=True)
"""

ppsql_conn = psycopg2.connect("dbname='freesound' user='freesound' password='%s'" % sys.argv[2])
ppsql_cur = ppsql_conn.cursor()
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"

unique_texts = {}
current_text_id = 1

while True:
    print start
    my_curs.execute("""select privmsgs_id, privmsgs_type, privmsgs_subject, privmsgs_from_userid, privmsgs_to_userid, FROM_UNIXTIME(privmsgs_date), privmsgs_text from phpbb_privmsgs inner join phpbb_privmsgs_text on phpbb_privmsgs.privmsg_id=phpbb_privmsgs_text.privmsgs_text_id limit %d, %d""" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, type, subject, from_user_id, to_user_id, date, text = row
        
        try:
            text_id = unique_texts[text]
        except KeyError:
            text_id = current_text_id
            unique_texts[text] = current_text_id
            current_text_id += 1
            # TODO: write text to file (removing \n and \t)
        
        if type in [1,5]:
            sent = 1
            archived = 0
            read = 0
        
            sent = 0
            archived = 0
            read = 0
        elif type == 0:
            sent = 0
            archived = 0
            read = 1
        elif type == 2:
            sent = 1
            archived = 0
            read = 0
        elif type == 3:
            sent = 0
            archived = 1
            read = 1
        elif type == 4:
            sent = 1
            archived = 1
            read = 1
                
        #output_file.write(u"\t".join(map(unicode, [id, user_id, object_id, content_type_id, lon, lat, zoom, created])) + "\n")

print """
copy geotags_geotag (id, user_id, object_id, content_type_id, lon, lat, zoom, created) from '%s';
vacuum analyze sounds_pack;
""" % output_filename