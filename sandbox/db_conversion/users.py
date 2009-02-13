import MySQLdb as my
import codecs
import sys
from text_utils import prepare_for_insert, smart_character_decoding

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1],db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False)
my_curs = my_conn.cursor()

start = 1 # start at one, we don't want the anonymous user!
granularity = 100000

while True:
    print start - 1
    my_curs.execute("SELECT user_id, user_active, username, user_password, FROM_UNIXTIME(user_regdate), FROM_UNIXTIME(user_lastvisit), user_email FROM phpbb_users limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    cleaned_data = []
    for row in rows:
        user_id, user_active, username, user_password, user_regdate, user_lastvisit, user_email = row
        
        username = smart_character_decoding(username)
        user_email = smart_character_decoding(user_email)
        
        username = username.replace(u"&amp;", u"&").replace(u"&lt;", u"<").replace(u"&gt;", u">").replace("&quot;","\"")
        
        if len(user_email) > 75:
            # skip users with crazy email addresses
            continue
        
        output_file.write(u"\t".join([unicode(user_id), unicode(user_active), username, user_password, unicode(user_regdate), unicode(user_lastvisit), user_email, u"", u"", "0", "0"]) + "\n")

print """
alter table auth_user drop constraint auth_user_username_key;
copy auth_user (id, is_active, username, password, date_joined, last_login, email, first_name, last_name, is_staff, is_superuser) from '%s';
select setval('auth_user_id_seq',(select max(id)+1 from auth_user));
vacuum analyze auth_user;

create table TEMP_TABLE as select select username from auth_user group by username having count(*) > 1;
delete from auth_user where username in (select username from TEMP_TABLE);
drop table TEMP_TABLE;

create table TEMP_TABLE as select email from auth_user group by email having count(*) > 1;
delete from auth_user where email in (select email from TEMP_TABLE) and last_login = '1970-01-01 01:00:00+01';
drop table TEMP_TABLE;

create table TEMP_TABLE as select lower(username) as username from auth_user group by lower(username) having count(*) > 1;
delete from auth_user where lower(username) in (select username from TEMP_TABLE) and last_login='1970-01-01 01:00:00+01';
drop table TEMP_TABLE;

update auth_user set is_staff=true, is_superuser=true where username='Bram';

alter table auth_user add constraint auth_user_username_key unique(username);
vacuum analyze auth_user;
""" % output_filename        