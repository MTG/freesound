import MySQLdb as my
import psycopg2
import codecs, sys, re
from text_utils import prepare_for_insert, smart_character_decoding

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False, use_unicode=False)
my_curs = my_conn.cursor()

start = 0
granularity = 1000

check_user_ids = True

if check_user_ids:
    ppsql_conn = psycopg2.connect("dbname='freesound' user='freesound' password='%s'" % sys.argv[1])
    ppsql_cur = ppsql_conn.cursor()
    print "getting all valid user ids"
    ppsql_cur.execute("SELECT id FROM auth_user")
    valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
    print "done"

valid_forum_ids = dict((id, 0) for id in [1, 3, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14])

sunk = 0
regular = 1
sticky = 2

while True:
    print start
    my_curs.execute("select topic_id, forum_id, topic_title, topic_poster, FROM_UNIXTIME(topic_time), topic_status, topic_type from phpbb_topics limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        topic_id, forum_id, topic_title, topic_poster, topic_time, topic_status, topic_type = row
        
        if (check_user_ids and topic_poster not in valid_user_ids) or (forum_id not in valid_forum_ids):
            continue
        
        topic_title = prepare_for_insert(smart_character_decoding(topic_title))

        status = regular
        
        if topic_status == 3: # moved
            print "don't know how to handle this..."
            sys.exit(0)
        if topic_type == 3: # post global announce
            print "don't know how to handle this..."
            sys.exit(0)

        if topic_status == 0: # unlocked
            status = regular
        if topic_type == 0: # normal
            status = regular
        
        if topic_type == 1: # sticky
            status = sticky
        if topic_type == 2: # announce
            status = sticky
#        
        if topic_status == 1: # locked!
            status = sunk

        all_vars = [topic_id, forum_id, topic_poster, topic_title, status, 0, None, topic_time]
        
        output_file.write(u"\t".join(map(unicode, all_vars)) + u"\n")

print """
copy forum_thread (id, forum_id, author_id, title, status, num_posts, last_post_id, created) from '%s' null as 'None';
select setval('forum_thread_id_seq',(select max(id)+1 from forum_thread));
vacuum analyze forum_thread;
""" % output_filename