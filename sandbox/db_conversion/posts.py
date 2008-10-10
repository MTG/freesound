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

    print "getting all valid thread ids"
    ppsql_cur.execute("SELECT id FROM forum_thread")
    valid_thread_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
    print "done"


while True:
    print start
    my_curs.execute("select p.post_id, p.topic_id, p.poster_id, FROM_UNIXTIME(p.post_time), t.post_text from phpbb_posts p inner join phpbb_posts_text t on p.post_id = t.post_id limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        post_id, topic_id, poster_id, post_time, post_text = row
        
        if (check_user_ids and poster_id not in valid_user_ids) or (topic_id not in valid_thread_ids):
            continue
        
        post_text = prepare_for_insert(smart_character_decoding(post_text))

        all_vars = [post_id, topic_id, poster_id, post_text, post_time]
        
        output_file.write(u"\t".join(map(unicode, all_vars)) + u"\n")
 
print """
copy forum_post (id, thread_id, author_id, body, created) from '%s' null as 'None';
select setval('forum_post_id_seq',(select max(id)+1 from forum_post));
vacuum analyze forum_post;
""" % output_filename