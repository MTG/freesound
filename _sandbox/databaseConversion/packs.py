from db_utils import get_mysql_cursor, queryrunner, get_user_ids
from text_utils import smart_character_decoding


VALID_USER_IDS = get_user_ids()


def transform_row_packs(row):
    rowid, name, user_id, created = row
    
    if user_id not in VALID_USER_IDS:
        return
    
    name = smart_character_decoding(name)
    
    description = ""
    is_dirty = "t"
    num_downloads = 0
    
    if rowid == 1420:
        user_id = 588695

    fields = [rowid, name, user_id, created, description, is_dirty, 
        num_downloads]
    print "\t".join(map(unicode, fields))


def migrate_packs(curs):
    print """copy sounds_pack (id, name, user_id, created, description, 
    is_dirty, num_downloads) from stdin;"""

    query = """SELECT ID, name, userID, date FROM audio_file_packs 
        WHERE (select audio_file.id from audio_file where 
        packID=audio_file_packs.id limit 1) is not null"""
    queryrunner(curs, query, transform_row_packs)
    print """\."""  

    print """
    select setval('sounds_pack_id_seq',(select max(id)+1 from sounds_pack));
    vacuum analyze sounds_pack;"""



def main():
    curs = get_mysql_cursor()
    migrate_packs(curs)

if __name__ == '__main__':
    main()
