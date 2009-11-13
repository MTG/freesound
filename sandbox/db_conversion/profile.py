import MySQLdb as my
import psycopg2
import codecs, sys, re
import time
from text_utils import prepare_for_insert, smart_character_decoding
from HTMLParser import HTMLParseError
from local_settings import *

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'w', 'utf-8', errors='strict')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

check_user_ids = True

if check_user_ids:
    ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
    ppsql_cur = ppsql_conn.cursor()
    print "getting all valid user ids"
    ppsql_cur.execute("SELECT id FROM auth_user")
    valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
    print "done"

start = 0
granularity = 100000

insert_id = 0

url_match = re.compile(r"^http:\/\/[\w_-]+\.[\.\w_-]+\/?[@\.\w/_\?=~;:%#&\+-]*$", re.IGNORECASE)

while True:
    print start
    
    my_curs.execute("""select
                            user_id,
                            user_website as home_page,
                            user_sig as signature,
                            (user_whitelist.userID is not null) as is_whitelisted,
                            users.text as about,
                            (email_ignore.userID is null) as wants_newsletter
                        from phpbb_users
                        left join user_whitelist on user_whitelist.userID=phpbb_users.user_id
                        left join users on users.userID=phpbb_users.user_id
                        left join email_ignore on email_ignore.userID=phpbb_users.user_id
                        limit %d, %d""" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        user_id, home_page, signature, is_whitelisted, about, wants_newsletter = row
        
        if home_page:
            home_page = smart_character_decoding(home_page)
        if signature:
            signature = smart_character_decoding(signature)
        if about:
            about = smart_character_decoding(about)
                    
        if not check_user_ids or user_id in valid_user_ids:
            if home_page:
                home_page = home_page.lower()
                split = home_page.split()
                if len(split) > 1:
                    home_page = split[0]
                
                if not url_match.match(home_page):
                    home_page = None

            if signature:
                signature = prepare_for_insert(signature)
            
            if about:
                try:
                    about = prepare_for_insert(about)
                except HTMLParseError:
                    about = ""
            
            geotag = None
            num_sounds = 0
            num_posts = 0
        
            output_file.write(u"\t".join(map(unicode, [insert_id, user_id, home_page, signature, is_whitelisted, about, wants_newsletter, geotag, num_sounds, num_posts])) + u"\n")
            insert_id += 1

print """
copy accounts_profile (id, user_id, home_page, signature, is_whitelisted, about, wants_newsletter, geotag_id, num_sounds, num_posts) from '%s' null as 'None';
select setval('accounts_profile_id_seq',(select max(id)+1 from accounts_profile));
vacuum analyze accounts_profile;
""" % output_filename        
