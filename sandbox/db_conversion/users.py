import MySQLdb as my
import codecs
import sys
from text_utils import prepare_for_insert, smart_character_decoding
from local_settings import *

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
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
        
        if user_id in (16967,1037753,1294123,99738,563934,697703,912954,960716,1401570,1404962,1414401,1437020,1453087,1488139,1533361,1567137,1574761,1626812,1665254,1677364,1700760,1712557,1717812,1741736,1770978,1840221,1840332):
            continue
        
        username = smart_character_decoding(username)
        user_email = smart_character_decoding(user_email)
        
        username = decode_htmlentities(username)
        
        if len(user_email) > 75:
            # skip users with crazy email addresses
            continue
        
        output_file.write(u"\t".join([unicode(user_id), unicode(user_active), username, user_password, unicode(user_regdate), unicode(user_lastvisit), user_email, u"", u"", "0", "0"]) + "\n")

print """
alter table auth_user drop constraint auth_user_username_key;
copy auth_user (id, is_active, username, password, date_joined, last_login, email, first_name, last_name, is_staff, is_superuser) from '%s';
select setval('auth_user_id_seq',(select max(id)+1 from auth_user));
vacuum analyze auth_user;

delete from auth_user where email in (select email from auth_user group by email having count(*) > 1) and last_login = '1970-01-01 01:00:00+01';
delete from auth_user where is_active = false and upper(username) in (select upper(username) from auth_user group by upper(username) having count(*) > 1);
delete from auth_user where last_login = '1970-01-01 01:00:00+01' and upper(username) in (select upper(username) from auth_user group by upper(username) having count(*) > 1);
delete from auth_user where id in (63988, 25491, 64476, 1294123, 898674, 166110, 543349);

update auth_user set is_staff=true, is_superuser=true where username='Bram';

create unique index auth_user_username_upper_key ON auth_user ((upper(username)));
vacuum analyze auth_user;
""" % output_filename
