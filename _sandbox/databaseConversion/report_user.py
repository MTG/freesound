#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Reads Freesound1 user_ids on command-line. Connects to a Mysql Freesound1
database and shows activity-related values:

    * is active
    * number of files
    * number of posts
    * number of articles
    * number of packs
    * date joined
    * last visit
"""

from local_settings import *
from optparse import OptionParser


class FreesoundUserInfo:
    """A class that shows information about a Freesound1 user."""

    def __init__(self, user_id):
        """Create a cursor.
        """
        self.conn = MySQLdb.connect(**MYSQL_CONNECT)
        self.curs = self.conn.cursor(DEFAULT_CURSORCLASS)
        self.user_id = user_id
        # List of (description, value) items.
        self.info = [('user_id', self.user_id)]

        self.get_data()


    def __put(self, label, query):
        """Retrieves value by executing query and stores it with a label.
        """
        self.curs.execute(query, self.user_id)
        self.info += [ (label, self.curs.fetchall()[0][0]) ]


    def get_data(self):
        """Gets information about the user.
        """
        self.__put("username",
            "SELECT username FROM phpbb_users WHERE user_id = %s ;") 
        self.__put("is_active",
            "SELECT user_active FROM phpbb_users WHERE user_id = %s ;") 
        self.__put("n_files",
            "SELECT count(*) FROM audio_file WHERE userID = %s ;") 
        self.__put("n_posts",
            "SELECT count(*) FROM phpbb_posts WHERE poster_id = %s ;")
        self.__put("n_articles",
            "SELECT count(*) FROM articles WHERE userID = %s ;")
        self.__put("n_packs",
            "SELECT count(*) FROM audio_file_packs WHERE userID = %s ;")
        self.__put("date_joined",
            """SELECT FROM_UNIXTIME(user_regdate) FROM phpbb_users 
                WHERE user_id = %s ;""")
        self.__put("last_visit",
            """SELECT FROM_UNIXTIME(user_lastvisit) FROM phpbb_users 
                WHERE user_id = %s ;""")


    def __str__(self):
        """Printable representation of self.info.
        """
        lines = [ 40*'#' + ' %s: %s' % self.info[0] ]
        lines += [ '%s: %s' % (k, v) for k, v in self.info[1:] ]
        return '\n'.join(lines)



def parse_command_line ():
    """Optparse wrapper.
    """
    usage = "usage: %prog <uid> [uid ...]"
    parser = OptionParser(usage=usage)
    options, args = parser.parse_args()

    if not args:
        parser.error("Please provide a user_id.")
    return (options, args)



def main():
    """Runs unless the file is imported.
    """

    # Parse command-line.
    ___, args = parse_command_line()

    for uid in args:
        print FreesoundUserInfo(uid)


if __name__ == '__main__':
    main()
