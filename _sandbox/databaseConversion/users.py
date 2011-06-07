#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate Freesound1 users (Mysql) to Freesound2 (Postgres).

Don't really imports anything, just prints generated SQL on stdout. 
This SQL must be run before other migration steps because it generates
the list of valid users needed later.
"""

from local_settings import *
from text_utils import smart_character_decoding, decode_htmlentities
import codecs
import hashlib
import base64
import sys
import traceback


OUT_FNAME = 'users.sql'
BANNED_USER_IDS = (
    16967,1037753,1294123,99738,563934,697703,912954,960716,1401570,1404962,
    1414401,1437020,1453087,1488139,1533361,1567137,1574761,1626812,1665254,
    1677364,1700760,1712557,1717812,1741736,1770978,1840221,1840332,
    1931670, 499086, 1347186, 1095376, 663394, 2089368, 1696334,
    1530283, 381353, 547677, 916210, 1088787, 1304475, 317824, 932069,
) + CUSTOM_BANNED_USERS




# got characters from rfc3986 (minus @, + which are valid for django usernames)
BAD_USERNAME_CHARACTERS = {':': '_colon_',
                           '/': '_slash_',
                           '?': '_qmark_',
                           '#': '_hash_',
                           '[': '_lbrack1_',
                           ']': '_rbrack1_',
                           '!': '_emark_',
                           '$': '_dollar_',
                           '&': '_amper_',
                           "'": '_quote_',
                           '(': '_lbrack2_',
                           ')': '_rbrack2_',
                           '*': '_stardom_',
                           ',': '_comma_',
                           ';': '_scolon_',
                           '=': '_equal_',
                           '{': '_lbrack3_',
                           '}': '_rbrack3_'
                           }


def transform_username_fs1fs2(fs1_name, fs2_append=''):
    """ Returns a tuple (changed, name) where changed is a boolean
        indicating the name was transformed and name a string
        with the correct username for freesound 2
    """
    if any([x in fs1_name for x in BAD_USERNAME_CHARACTERS.keys()]):
        fs2_name = fs1_name
        for bad_char, replacement in BAD_USERNAME_CHARACTERS.items():
            fs2_name = fs2_name.replace(bad_char, replacement)
        fs2_name = '%s%s' % (fs2_name, fs2_append)

        # If the transformed name is too long, create a hash.
        if len(fs2_name) > 30:
            try:
                m = hashlib.md5()
                m.update(fs2_name.encode('utf-8'))
            except UnicodeEncodeError:
                print 10*'#', fs1_name, fs2_name
            # Hack: m.hexdigest() is too long.
            fs2_name = base64.urlsafe_b64encode(m.digest())
        return True, fs2_name
    else:
        return False, fs1_name




def transform_row_users(row): 
    """Transforms a row of phpbb_user.

    Gets the row items instead of a tuple; returns a list, or None
    if the user is invalid.
    """
    user_id, user_active, username, user_password, user_regdate, \
        user_lastvisit, user_email = row

    if user_id in BANNED_USER_IDS:
        return
    # skip users with crazy email addresses
    if len(user_email) > 75:
        return 
    
    username = transform_username_fs1fs2(
            decode_htmlentities(
                smart_character_decoding(username)))[1]
    user_email = smart_character_decoding(user_email)

    fields = [
        unicode(user_id), unicode(user_active), username, user_password,
        unicode(user_regdate), unicode(user_lastvisit), user_email, 
        u"", u"", "0", "0",
    ]
    return fields



def migrate_users(curs):

    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql_header = """
-- 
-- Table phpbb_users
-- 
ALTER TABLE auth_user DROP CONSTRAINT auth_user_username_key;
COPY auth_user (id, is_active, username, password, date_joined, 
    last_login, email, first_name, last_name, is_staff, is_superuser) 
    FROM stdin ;
"""
    out.write(sql_header)

    query = """SELECT user_id, user_active, username, user_password, 
        FROM_UNIXTIME(user_regdate), FROM_UNIXTIME(user_lastvisit), 
        user_email FROM phpbb_users"""
        #WHERE user_id = 2 or user_id = 432878 or user_id = 1931670;"""
    curs.execute(query)

    # start at one, we don't want the anonymous user!
    ___ = curs.fetchone()
    
    while True:
        row = curs.fetchone()
        if not row:
            break
        new_row = transform_row_users(row)
        if new_row:
            try:
                out.write(u"\t".join(new_row) + "\n")
            except:
                traceback.print_exc()
                traceback.print_stack()
                print "### phantom unicode error here"
                print new_row

    sql_tail = """\.

    SELECT SETVAL('auth_user_id_seq',(select max(id)+1 from auth_user));
    VACUUM ANALYZE auth_user;

    --- Duplicated emails, never logged in.
    ---
    DELETE FROM auth_user WHERE 
        email IN (
            SELECT email FROM auth_user GROUP BY email HAVING COUNT(*) > 1) 
        AND last_login = '1970-01-01 01:00:00+01';

    --- Users that:
    ---  a) Never completed registration.
    ---  b) The (converted) username collides with another username. 
    ---
    DELETE FROM auth_user WHERE 
        is_active = false AND UPPER(username) IN (
            SELECT UPPER(username) FROM auth_user GROUP BY UPPER(username) 
            HAVING COUNT(*) > 1
        );

    --- Never logged in and (converted) username collides with another.
    ---
    DELETE FROM auth_user WHERE 
        last_login = '1970-01-01 01:00:00+01' 
        AND upper(username) IN (
            SELECT UPPER(username) FROM auth_user GROUP BY UPPER(username) 
            HAVING COUNT(*) > 1
        );

    DELETE FROM auth_user WHERE id IN 
        (63988, 25491, 64476, 1294123, 898674, 166110, 543349);

    UPDATE auth_user SET is_staff=true, is_superuser=true WHERE username='Bram';

    --- Don't run this before removing all duplicate usernames.
    --- Will fail.
    --- CREATE UNIQUE INDEX auth_user_username_upper_key ON 
    ---    auth_user ((UPPER(username)));
    ---
    ---
    VACUUM ANALYZE auth_user;

    --
    -- End of phpbb_users
    --
    """
    out.write(sql_tail)



def main():
    conn = MySQLdb.connect(**MYSQL_CONNECT)
    curs = conn.cursor(DEFAULT_CURSORCLASS)
    migrate_users(curs)

if __name__ == '__main__':
    main()
