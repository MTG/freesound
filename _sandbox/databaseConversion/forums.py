from django.template.defaultfilters import slugify
from text_utils import smart_character_decoding
import MySQLdb as my
import codecs
from local_settings import *

output_filename = '/tmp/importfile.dat'
output_file = codecs.open(output_filename, 'wt', 'utf-8')

my_conn = my.connect(**MYSQL_CONNECT)
my_curs = my_conn.cursor()

my_curs.execute("select forum_id, forum_name, forum_desc, forum_order from phpbb_forums")
rows = my_curs.fetchall()

for row in rows:
    forum_id, forum_name, forum_desc, forum_order = row
    
    forum_name = smart_character_decoding(forum_name)
    forum_desc = smart_character_decoding(forum_desc)
    
    forum_name_slug = slugify(forum_name)
    
    output_file.write(u"\t".join(map(unicode, [forum_id, forum_order, forum_name, forum_name_slug, forum_desc, 0, None, 0])) + "\n")

print """
copy forum_forum (id, "order", name, name_slug, description, num_threads, last_post_id, num_posts) from '%s' null as 'None';
select setval('forum_forum_id_seq',(select max(id)+1 from forum_forum));
vacuum analyze forum_forum;
""" % output_filename




