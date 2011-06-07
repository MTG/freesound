#!/usr/bin/env python
# -*- coding: utf-8 -*-

from local_settings import *
import codecs
from db_utils import get_user_ids, get_sound_ids, get_content_id
from text_utils import smart_character_decoding
from sets import Set
import re

OUT_FNAME = 'tags.sql'
OUT_TAGGEDITEM_FNAME = 'tags_taggeditem.sql'
OUT_MAPPING_FNAME = 'tags_fs1tag.sql'

VALID_USER_IDS = get_user_ids()
VALID_SOUND_IDS = get_sound_ids()
CONTENT_TYPE_ID = get_content_id('sounds', 'sound')


ALPHANUM_ONLY = re.compile(r"[^ a-zA-Z0-9-]")
MULTI_DASHES = re.compile(r"-+")


# Global counter.
tag_id = 0
# Store { tag: tag_id } values for every tag.
lookup_dict = {}
# Store { hash: tag_id } values for every tag.
UNIQUE_TEST = {}
# Store unique { fs1_tag_id: fs2_tag_id } mappings.
OLD_TAG_MAP = {}




def clean_and_split_tags(tags):
    tags = ALPHANUM_ONLY.sub("", tags)
    tags = MULTI_DASHES.sub("-", tags)
    common_words = """the of to and an in is it you that he was for 
        on are with as i his they be at""".split()
    return Set([tag for tag in [tag.strip('-') for tag in tags.split()] if tag and tag not in common_words])    


def tag_lookup(tag):
    global tag_id
    global lookup_dict
    
    try:
        return lookup_dict[tag]
    except KeyError:
        lookup_dict[tag] = tag_id
        tag_id += 1
        return lookup_dict[tag]




def migrate_taggeditem():

    global UNIQUE_TEST
    global OLD_TAG_MAP 

    out_taggeditem = codecs.open(OUT_TAGGEDITEM_FNAME, 'wt', 'utf-8')
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)



    sql = """COPY tags_taggeditem (id, user_id, tag_id, content_type_id, 
        object_id, created) FROM stdin ;
"""
    out_taggeditem.write(sql)


    query = """select audio_file_tag.ID, AudioFileID, userID, tagID, date, tag
        from audio_file_tag left join tags on audio_file_tag.tagId = tags.id 
        where tag is not null"""
    curs.execute(query)
    while True:
        row = curs.fetchone()
        if not row:
            break
        
        try:
            ID, AudioFileID, userID, tagID, date, tags = row
            
            tags = smart_character_decoding(tags, True)
            
            if not AudioFileID in VALID_SOUND_IDS or \
                    not userID in VALID_USER_IDS:
                continue
            
            for tag in clean_and_split_tags(tags):
                tid = tag_lookup(tag)
                
                if len(tag) > 100:
                    print AudioFileID, tag
                    continue

                hash = "%d %d %d" % (userID, tid, AudioFileID)
                if hash in UNIQUE_TEST:
                    print "\tduplicate tag", AudioFileID, tag, tid
                else:
                    UNIQUE_TEST[hash] = 1
                    fields = [ID, userID, tid, CONTENT_TYPE_ID, AudioFileID, date]
                    line = u"\t".join(map(unicode, fields)) + u"\n" 
                    out_taggeditem.write(line)

                    # Save a mapping of old tags.id to the new tags_tag.id
                    OLD_TAG_MAP.setdefault(tagID, tid)
                    
        except TypeError:
            print tag


    sql = """\.

    select setval('tags_taggeditem_id_seq',(select max(id)+1 from tags_taggeditem));
    vacuum analyze tags_taggeditem;
    """
    out_taggeditem.write(sql)




def migrate_tags():
# This file can't be generated until lookup_dict has been completed.
# But this file MUST be imported before the other one.
    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """copy tags_tag (name, id) from stdin;
"""
    out.write(sql)

    lines = [u"\t".join(map(unicode, item)) for item in lookup_dict.items()]
    out.write(u"\n".join(lines))

    sql = """\.
    SELECT SETVAL('tags_tag_id_seq',(SELECT MAX(id)+1 FROM tags_tag));
    VACUUM ANALYZE tags_tag;
    """
    out.write(sql)



def migrate_tags_mapping():

    out = codecs.open(OUT_MAPPING_FNAME, 'wt', 'utf-8')

    sql = """copy tags_fs1tag (id, fs1_id, tag_id) from stdin;
"""
    out.write(sql)

    idx = 0 
    fields = []
    for fs1_id, fs2_id in OLD_TAG_MAP.items():
        fields.append( (idx, fs1_id, fs2_id) )
        idx += 1
        
    lines = [u"\t".join(map(unicode, f)) for f in fields]
    out.write(u"\n".join(lines) + u"\n")

    sql = """\.
    SELECT SETVAL('tags_fs1tag_fs1_id_seq',
        (SELECT MAX(id)+1 FROM tags_fs1tag));
    VACUUM ANALYZE tags_tag;
    """
    out.write(sql)





if __name__ == '__main__':
    migrate_taggeditem()
    migrate_tags()
    migrate_tags_mapping()

