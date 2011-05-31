#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""users_reindex must be run after users are created and unexpeted duplicated
users have been removed from the database. Otherwise 'CREATE INDEX' fails.
"""

import codecs

OUT_FNAME = 'users_reindex.sql'


def index_users():
    out = codecs.open(OUT_FNAME, 'wt', 'utf-8')

    sql = """
    CREATE UNIQUE INDEX auth_user_username_upper_key ON 
        auth_user ((UPPER(username)));
    VACUUM ANALYZE auth_user;
    """
    out.write(sql)



def main():
    index_users()

if __name__ == '__main__':
    main()
