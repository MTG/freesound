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
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"

start = 0
granularity = 10000

md5s = {}

missing_files = [49525, 57342, 57343, 57346, 57355]

while True:
    print start
    my_curs.execute("SELECT ID, originalFilename, userID, duration, bitrate, bitdepth, filesize, dateAdded, samplerate, channels, packID, moderated, badDescription, md5, newFilename, extension FROM audio_file ORDER BY dateAdded limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, original_filename, user_id, duration, bitrate, bitdepth, filesize, created, samplerate, channels, pack_id, moderation_state, moderation_bad_description, md5, base_filename_slug, type = row
        
        if user_id not in valid_user_ids:
            continue
        
        original_filename = smart_character_decoding(original_filename)
        
        if id in missing_files:
            continue
        
        if md5 in md5s:
            continue
        else:
            md5s[md5] = 1
        
        my_curs.execute("SELECT text FROM audio_file_text_description where audioFileId = %d" % id)
        
        descriptions = []
        for d in my_curs.fetchall():
            descriptions.append(smart_character_decoding(d[0]))

        description = prepare_for_insert( u"\n".join(descriptions))
        
        original_path = None
        moderation_date = created
        processing_date = created
        processing_state = "OK"
        license_id = 1
        processing_log = None
        
        type = type.lower()
        
        if moderation_state in [0,3]:
            moderation_state = "PE"
        elif moderation_state == 1:
            moderation_state = "OK"
        elif moderation_state in [2,4]:
            moderation_state = "DE"
            
        moderation_bad_description = "f" if moderation_bad_description == 0 else "t"
        
        geotag = None
        num_comments = 0
        num_downloads = 0
        avg_rating = 0
        num_ratings = 0
        
        all_vars = [id,
            user_id,
            created,
            original_path,
            base_filename_slug,
            description,
            license_id,
            original_filename,
            pack_id,
            type,
            duration,
            bitrate,
            bitdepth,
            samplerate,
            filesize,
            channels,
            md5,
            moderation_state,
            moderation_date,
            moderation_bad_description,
            processing_state,
            processing_date,
            processing_log,
            geotag, num_comments, num_downloads, avg_rating, num_ratings]
        
        output_file.write(u"\t".join(map(unicode, all_vars)) + "\n")

print """
copy sounds_sound (id, user_id, created, original_path, base_filename_slug, description, license_id, original_filename, pack_id, type, duration, bitrate, bitdepth, samplerate, filesize, channels, md5, moderation_state, moderation_date, has_bad_description, processing_state, processing_date, processing_log, geotag_id, num_comments, num_downloads, avg_rating, num_ratings) from '%s' null as 'None';
select setval('sounds_sound_id_seq',(select max(id)+1 from sounds_sound));
vacuum analyze sounds_sound;
""" % output_filename