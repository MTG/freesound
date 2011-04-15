import psycopg2
import time

ppsql_conn = psycopg2.connect("dbname='freesound' user='freesound' password='m1dn1ght'")

ppsql_cur = ppsql_conn.cursor()
ppsql_cur.execute("SELECT id, date_joined FROM auth_user WHERE is_active=true order by id")
print "fetching users"
users = dict((user_id, (joined, 0, 0)) for (user_id, joined) in ppsql_cur.fetchall())
print "done"

tables = [
			("comments_comment", "user_id"),
			("sounds_sound", "user_id"),
			("tags_taggeditem", "user_id"),
			("forum_post", "author_id"),
			("forum_thread", "author_id"),
			("ratings_rating", "user_id"),
			("geotags_geotag", "user_id"),
			("messages_message", "user_from_id")
			]

for table, field in tables:
	query = "select %s, max(created), count(*) from %s group by %s" % (field, table, field)

	print query
	ppsql_cur = ppsql_conn.cursor()
	ppsql_cur.execute(query)

	for user_id, action_date, action_count in ppsql_cur.fetchall():
		try:
			(date_joined, actions, days) = users[user_id]
			actions += action_count
			days = max(days, (action_date - date_joined).days)
			users[user_id] = (date_joined, actions, days)
		except KeyError:
			#print "user %d is non-active but has action!" % user_id
			pass

output = file("stats.txt", "w")

n_active = 0
n_passive = 0

for user_id, (joined, actions, days) in users.iteritems():
	if actions != 0 or days != 0:
		output.write("%d\t%d\n" % (actions, days))
		n_active += 1
	else:
		n_passive += 1

print "active", n_active
print "passive", n_passive