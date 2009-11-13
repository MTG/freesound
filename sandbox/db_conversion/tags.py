from local_settings import *
from text_utils import smart_character_decoding
import MySQLdb as my
from sets import Set
import codecs
import psycopg2
import re

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

output_filename2 = '/tmp/importfile2.dat'
output_file2 = codecs.open(output_filename2, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

ppsql_conn = psycopg2.connect(POSTGRES_CONNECT)
ppsql_cur = ppsql_conn.cursor()
print "getting all valid sound ids"
ppsql_cur.execute("SELECT id FROM sounds_sound")
valid_sound_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"
print "getting all valid user ids"
ppsql_cur.execute("SELECT id FROM auth_user")
valid_user_ids = dict((row[0],1) for row in ppsql_cur.fetchall())
print "done"

start = 0
granularity = 100000

alphanum_only = re.compile(r"[^ a-zA-Z0-9-]")
multi_dashes = re.compile(r"-+")

def clean_and_split_tags(tags):
    tags = alphanum_only.sub("", tags)
    tags = multi_dashes.sub("-", tags)
    common_words = "the of to and an in is it you that he was for on are with as i his they be at".split()
    return Set([tag for tag in [tag.strip('-') for tag in tags.split()] if tag and tag not in common_words])    

tag_id = 0
lookup_dict = {}

def tag_lookup(tag):
    global tag_id
    global lookup_dict
    
    try:
        return lookup_dict[tag]
    except KeyError:
        lookup_dict[tag] = tag_id
        tag_id += 1
        return lookup_dict[tag]

content_type_id = 19

unique_test = {}

while True:
    print start

    my_curs.execute("select audio_file_tag.ID, AudioFileID, userID, tagID, date, tag from audio_file_tag left join tags on audio_file_tag.tagId = tags.id where tag is not null limit %d, %d" % (start, granularity))
    rows = my_curs.fetchall()
    start += len(rows)
    
    if len(rows) == 0:
        break
    
    cleaned_data = []
    for row in rows:
        try:
            ID, AudioFileID, userID, tagID, date, tags = row
            
            tags = smart_character_decoding(tags, True)
            
            if not AudioFileID in valid_sound_ids or not userID in valid_user_ids:
                continue
            
            for tag in clean_and_split_tags(tags):
                tid = tag_lookup(tag)
                
                if len(tag) > 100:
                    print AudioFileID, tag
                    continue

                hash = "%d %d %d" % (userID, tid, AudioFileID)
                if hash in unique_test:
                    print "\tduplicate tag", AudioFileID, tag, tid
                else:
                    unique_test[hash] = 1
                    output_file.write(u"\t".join(map(unicode, [ID, userID, tid, content_type_id, AudioFileID, date])) + "\n")
        except TypeError:
            print tag

output_file2.write(u"\n".join([u"\t".join(map(unicode, item)) for item in lookup_dict.items()]))


print """
copy tags_tag (name, id) from '%s';
select setval('tags_tag_id_seq',(select max(id)+1 from tags_tag));
vacuum analyze tags_tag;
copy tags_taggeditem (id, user_id, tag_id, content_type_id, object_id, created) from '%s';
select setval('tags_taggeditem_id_seq',(select max(id)+1 from tags_taggeditem));
vacuum analyze tags_taggeditem;
""" % (output_filename2, output_filename)