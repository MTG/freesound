import MySQLdb as my
import codecs, sys, re
from text_utils import prepare_for_insert, smart_character_decoding

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(host="localhost", user="freesound", passwd=sys.argv[1], db="freesound", unix_socket="/var/mysql/mysql.sock", use_unicode=False)
my_curs = my_conn.cursor()

start = 0
granularity = 10000

dup_sounds = [13300, 5979, 13216, 11216, 39633, 53746, 16732, 8379, 51906, 14098, 9897, 2874, 47442, 13312, 55043, 55026, 55048, 55040, 55058, 9589, 133, 16731, 16733, 16733, 16734, 47441, 2406, 26718, 39631, 39634, 41198, 5301, 2905, 7187, 2194, 1393, 5299, 5989]

missing_files = [49525, 57342, 57343, 57346, 57355]

while True:
    print start
    my_curs.execute("SELECT ID, originalFilename, userID, duration, bitrate, bitdepth, filesize, dateAdded, samplerate, channels, packID, moderated, badDescription, md5, newFilename, extension FROM audio_file limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    for row in rows:
        id, original_filename, user_id, duration, bitrate, bitdepth, filesize, created, samplerate, channels, pack_id, moderation_state, moderation_bad_description, md5, base_filename_slug, type = row
        
        original_filename = smart_character_decoding(original_filename)
        
        if id in dup_sounds or id in missing_files:
            continue
        
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
            geotag]
        
        output_file.write(u"\t".join(map(unicode, all_vars)) + "\n")

print """
copy sounds_sound (id, user_id, created, original_path, base_filename_slug, description, license_id, original_filename, pack_id, type, duration, bitrate, bitdepth, samplerate, filesize, channels, md5, moderation_state, moderation_date, has_bad_description, processing_state, processing_date, processing_log, geotag) from '%s' null as 'None';
select setval('sounds_sound_id_seq',(select max(id)+1 from sounds_sound));
vacuum analyze sounds_sound;
""" % output_filename