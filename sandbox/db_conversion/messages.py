import MySQLdb as my
import codecs
import sys
import psycopg2
from text_utils import prepare_for_insert, smart_character_decoding
import re

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

output_filename2 = '/tmp/importfile2.dat'
output_file2 = codecs.open(output_filename2, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False)
my_curs = my_conn.cursor()

content_type_id = 18

start = 0
granularity = 10000

ppsql_conn = psycopg2.connect("dbname='freesound' user='freesound' password='%s'" % sys.argv[1])
ppsql_cur = ppsql_conn.cursor()
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((int(row[0]),1) for row in ppsql_cur.fetchall())
print "done, gotten", len(valid_user_ids), "ids"

unique_texts = {}
current_text_id = 1

n_messages = 0
n_ignored = 0

message_id = 0

while True:
    print start
    my_curs.execute("""select privmsgs_id, privmsgs_type, privmsgs_subject, privmsgs_from_userid, privmsgs_to_userid, FROM_UNIXTIME(privmsgs_date), privmsgs_text from phpbb_privmsgs inner join phpbb_privmsgs_text on phpbb_privmsgs.privmsgs_id=phpbb_privmsgs_text.privmsgs_text_id limit %d, %d""" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, type, subject, user_from_id, user_to_id, created, text = row
        
        if subject:
            subject = smart_character_decoding(subject)
        if text:
            text = smart_character_decoding(text)
        
        n_messages += 1
        
        if user_from_id not in valid_user_ids or user_to_id not in valid_user_ids:
            print "ignoring message from", user_from_id, "to", user_to_id
            n_ignored += 1
        
        try:
            text_id = unique_texts[text]
        except KeyError:
            text_id = current_text_id
            unique_texts[text] = current_text_id
            current_text_id += 1
            
            text = prepare_for_insert( text, True )

            output_file.write(u"\t".join(map(unicode, [text_id, text])) + "\n")
        
        subject = prepare_for_insert(subject, html_code=False, bb_code=False)
        
        body_id = text_id
        
        if type in [1,5]:
            is_sent = 1
            is_archived = 0
            is_read = 0
                
            output_file2.write(u"\t".join(map(unicode, [message_id, user_from_id, user_to_id, subject, body_id, is_sent, is_read, is_archived, created])) + "\n")
            message_id += 1
        
            is_sent = 0
            is_archived = 0
            is_read = 0
        elif type == 0:
            is_sent = 0
            is_archived = 0
            is_read = 1
        elif type == 2:
            is_sent = 1
            is_archived = 0
            is_read = 0
        elif type == 3:
            is_sent = 0
            is_archived = 1
            is_read = 1
        elif type == 4:
            is_sent = 1
            is_archived = 1
            is_read = 1
                
        output_file2.write(u"\t".join(map(unicode, [message_id, user_from_id, user_to_id, subject, body_id, is_sent, is_read, is_archived, created])) + "\n")
        message_id += 1

print "messages", n_messages
print "ignored", n_ignored

print """
copy messages_messagebody (id, body) from '%s';
select setval('messages_messagebody_id_seq',(select max(id)+1 from messages_messagebody));
vacuum analyze messages_messagebody;
copy messages_message (id, user_from_id, user_to_id, subject, body_id, is_sent, is_read, is_archived, created) from '%s';
select setval('messages_message_id_seq',(select max(id)+1 from messages_message));
vacuum analyze messages_message;
""" % (output_filename, output_filename2)