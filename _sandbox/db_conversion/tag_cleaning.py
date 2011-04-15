import psycopg2, operator, sys

def get_google_results(string):
    try:
        import urllib, simplejson
        encoded = urllib.urlencode({"q": '"' + string + '"'})
        return int(simplejson.loads(urllib.urlopen("http://ajax.googleapis.com/ajax/services/search/web?v=1.0&" + encoded).read())["responseData"]["cursor"]["estimatedResultCount"])
    except KeyError:
        return 0

print "getting all tags"

ppsql_conn = psycopg2.connect("dbname='freesound' user='freesound' password='%s'" % sys.argv[1])
ppsql_cur = ppsql_conn.cursor()
ppsql_cur.execute("select object_id, pegar(name) from tags_taggeditem I left join tags_tag T on T.id=I.tag_id group by object_id;")

sounds_tags = [row[1].split() for row in ppsql_cur.fetchall()]

print len(sounds_tags)

print "getting dashed"

dashed_tags = {}

for tags in sounds_tags:
    for tag in tags:
        if '-' in tag:
            try:
                dashed_tags[tag] += 1
            except KeyError:
                dashed_tags[tag] = 1

print "finding matches"

important = sorted(dashed_tags.items(), key=operator.itemgetter(1), reverse=True)[0:20]

results = dict((dashed, {"hits":nr_hits, "separate_parts":0, "joined_parts":0}) for (dashed, nr_hits) in important)

for (dashed, nr_hits) in important:
    dashed_parts = dashed.split('-')
    for tags in sounds_tags:
        if dashed in tags:
            continue
        if all(part in tags for part in dashed_parts):
            #print dashed, tags
            results[dashed]["separate_parts"] += 1


for (dashed, nr_hits) in important:
    dashed_nodash = dashed.replace('-', '')
    for tags in sounds_tags:
        if dashed_nodash in tags:
            #print dashed, tags
            results[dashed]["joined_parts"] += 1

for (tag, result) in results.iteritems():
    print tag, result["hits"]
    print " ".join(tag.split("-")), result["separate_parts"]
    print "".join(tag.split("-")), result["joined_parts"]
    
    results_separate = get_google_results(tag)
    results_joined = get_google_results("".join(tag.split("-")))
    
    print "google gets most results for:",
    
    if results_separate > results_joined:
        print tag, "(", results_separate, "versus", results_joined, ")"
    else:
        print "".join(tag.split("-")), "(", results_joined, "versus", results_separate, ")"

    print 