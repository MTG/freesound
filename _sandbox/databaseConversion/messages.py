#!/usr/bin/env python
# -*- coding: utf-8 -*-

from local_settings import *
import codecs
from db_utils import get_user_ids
from text_utils import prepare_for_insert, smart_character_decoding, \
    decode_htmlentities

OUT_MSG_FNAME = 'messages.sql'
OUT_BODY_FNAME = 'messages_body.sql'

VALID_USER_IDS = get_user_ids()


# Dictionary of texts. Key: 'text' field; value: 'text_id' generated field.
UNIQUE_TEXTS = {}
# Incremental index for processed texts.
CURRENT_TEXT_ID = 1
# Counter.
N_MESSAGES = 0
# Counter.
N_IGNORED = 0
# 
MESSAGE_ID = 0



def transform_row(row):
    ___, msgtype, subject, user_from_id, user_to_id, created, text = row
    
    global UNIQUE_TEXTS 
    global CURRENT_TEXT_ID 
    global N_MESSAGES 
    global N_IGNORED
    global MESSAGE_ID

    messagebody = None

    if subject:
        subject = decode_htmlentities(smart_character_decoding(subject))
    if text:
        text = smart_character_decoding(text)
    
    N_MESSAGES += 1
    
    # Do nothing if sender or receiver is an invalid user.
    if user_from_id not in VALID_USER_IDS or \
            user_to_id not in VALID_USER_IDS:
        print "ignoring message from", user_from_id, "to", user_to_id
        N_IGNORED += 1
        return None, None
    

    try:
        text_id = UNIQUE_TEXTS[text]
    except KeyError:
        # This is the first time the text shows up.
        # Assign a text_id and add to the global dict.
        text_id = CURRENT_TEXT_ID
        UNIQUE_TEXTS[text] = CURRENT_TEXT_ID
        CURRENT_TEXT_ID += 1
        
        # Text must be inserted as 'messagebody'.
        text = prepare_for_insert( text, True )
        messagebody = map(unicode, [text_id, text])
    

    subject = prepare_for_insert(subject, html_code=False, bb_code=False)
    
    body_id = text_id
    
    if msgtype in [1, 5]:
        is_sent, is_archived, is_read = 1, 0, 0
            
        # We store the message twice: once for the sender, once for
        # the receiver. See messages/models.py.
        message = map(unicode, [MESSAGE_ID, user_from_id, user_to_id, 
            subject, body_id, is_sent, is_read, is_archived, created])
        MESSAGE_ID += 1
    
        is_sent, is_archived, is_read = 0, 0, 0
    elif msgtype == 0:
        is_sent, is_archived, is_read = 0, 0, 1
    elif msgtype == 2:
        is_sent, is_archived, is_read = 1, 0, 0
    elif msgtype == 3:
        is_sent, is_archived, is_read = 0, 1, 1
    elif msgtype == 4:
        is_sent, is_archived, is_read = 1, 1, 1
            
    message = map(unicode, [MESSAGE_ID, user_from_id, user_to_id, 
        subject, body_id, is_sent, is_read, is_archived, created])
    MESSAGE_ID += 1

    return messagebody, message








def migrate_messages(curs):

    # Use one file for every table.
    out_body = codecs.open(OUT_BODY_FNAME, 'wt', 'utf-8')
    out_msg = codecs.open(OUT_MSG_FNAME, 'wt', 'utf-8')

    # Write headers for both files.
    sql = """copy messages_messagebody (id, body) from stdin ;
"""
    out_body.write(sql)
    #
    sql = """copy messages_message (id, user_from_id, user_to_id, subject, 
        body_id, is_sent, is_read, is_archived, created) from stdin ;
"""
    out_msg.write(sql)


    query = """SELECT privmsgs_id, privmsgs_type, privmsgs_subject,
        privmsgs_from_userid, privmsgs_to_userid, FROM_UNIXTIME(privmsgs_date),
        privmsgs_text 
    FROM phpbb_privmsgs 
    INNER JOIN phpbb_privmsgs_text 
    ON phpbb_privmsgs.privmsgs_id=phpbb_privmsgs_text.privmsgs_text_id
    """
    curs.execute(query)
    
    while True:
        row = curs.fetchone()
        if not row:
            break
        messagebody, message = transform_row(row)

        if messagebody:
            out_body.write(u"\t".join(messagebody) + u"\n" )
        if message:
            out_msg.write(u"\t".join(message) + u"\n" )

    # Write tail for both files.
    sql = """\.
    select setval('messages_messagebody_id_seq',(select max(id)+1 
    from messages_messagebody));
    vacuum analyze messages_messagebody;
    """
    out_body.write(sql)
    sql = """\.
    select setval('messages_message_id_seq',(select max(id)+1 
    from messages_message));
    vacuum analyze messages_message;
    """
    out_msg.write(sql)

    print "messages", N_MESSAGES
    print "ignored", N_IGNORED





def main():
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_messages(curs)

if __name__ == '__main__':
    main()
