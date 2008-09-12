import MySQLdb as my
import codecs
from django.template.defaultfilters import slugify

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd="m1dn1ght",db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=True)
my_curs = my_conn.cursor()

start = 0
granularity = 1000

while True:
    print start
    my_curs.execute("SELECT ID, name, userID, date FROM audio_file_packs WHERE (select audio_file.id from audio_file where packID=audio_file_packs.id limit 1) is not null limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    cleaned_data = []
    for row in rows:
        id, name, user_id, created = row
        description = ""
        name_slug = slugify(name)
        
        if id == 1420:
            user_id = 588695;
        
        output_file.write(u"\t".join(map(unicode, [id, name, user_id, created, description, name_slug])) + "\n")

print """
copy sounds_pack (id, name, user_id, created, description, name_slug) from '%s';
vacuum analyze sounds_pack;
""" % output_filename