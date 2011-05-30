from db_utils import get_mysql_cursor, get_user_ids, get_sound_ids, get_content_id
from text_utils import smart_character_decoding
from sets import Set
import re

valid_user_ids = get_user_ids()
valid_sound_ids = get_sound_ids()
content_type_id = get_content_id('sounds', 'sound')


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

unique_test = {}

print """copy tags_tag (name, id) from stdin;"""
print u"\n".join([u"\t".join(map(unicode, item)) for item in lookup_dict.items()])
print """\.
select setval('tags_tag_id_seq',(select max(id)+1 from tags_tag));
vacuum analyze tags_tag;"""

print """copy tags_taggeditem (id, user_id, tag_id, content_type_id, object_id, created) from stin;"""

my_curs = get_mysql_cursor()
query = """select audio_file_tag.ID, AudioFileID, userID, tagID, date, tag
    from audio_file_tag left join tags on audio_file_tag.tagId = tags.id where
    tag is not null"""
my_curs.execute(query)
while True:
    row = my_curs.fetchone()
    if not row:
        break
    
    cleaned_data = []
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
                print u"\t".join(map(unicode, [ID, userID, tid, content_type_id, AudioFileID, date]))
    except TypeError:
        print tag


print """\."""
print """
select setval('tags_taggeditem_id_seq',(select max(id)+1 from tags_taggeditem));
vacuum analyze tags_taggeditem;
"""

