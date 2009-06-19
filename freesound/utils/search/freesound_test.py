import time
from solr import *

"""An example of usage, with the freesound custom schema...
"""

solr = Solr("http://localhost:8983/solr/", persistent=True)

lines = file("searches").readlines()
lines.reverse()

num_queries_total = 0
num_queries_this_loop = 0

time_solr = 0
results_solr = 0
results_before = 0

start = time.time()
start_this_loop = start

for index, line in enumerate(lines):
    if index % 200 == 0 and index > 0:
        avg_total = ((time.time() - start_this_loop) * 1000) / float(num_queries_this_loop)
        avg_solr = time_solr / float(num_queries_this_loop)
        avg_python = avg_total - avg_solr
        
        print "Batch of", num_queries_this_loop, "queries. Total queries:", num_queries_total
        print "\tAverage total time:", avg_total
        print "\tAverage solr:", avg_solr
        print "\tAverage python:", avg_python
        print "\tIndex:", index
        print "\tResult quality increase: %d%%" % int((100.0*results_solr)/float(results_before))

        num_queries_this_loop = 0
        time_solr = 0
        results_solr = 0
        results_before = 0
        start_this_loop = time.time()
                        
    try:
        try:
            (search, count) = line.strip().split("\t")
        except ValueError:
            continue
        
        count = int(count)

        results_before += count

        # clean the only few things DisMax doesn't like... :)
        search = search.strip("+-").replace("--", "").replace("+-", "").replace("-+", "").replace("++", "")
        if search == "\"" or search == "\"\"":
            search = ""

        query = SolrQuery()
        query.set_dismax_query(search, query_fields=[("id", 4), ("tag",3), ("description",3), ("username",2), ("pack_original",2), ("filename",2), "comment"])
        query.set_query_options(start=0, rows=10, field_list=["id"])
        query.add_facet_fields("samplerate", "pack_original", "username", "tag", "bitrate", "bitdepth")
        query.set_facet_options_default(limit=5, sort=True, mincount=1, count_missing=True)
        query.set_facet_options("tag", limit=30)
        query.set_facet_options("username", limit=30)
        
        response = solr.select(unicode(query))
        interpreted = SolrResponseInterpreter(response)

        num_queries_total += 1
        num_queries_this_loop += 1
        
        time_solr += interpreted.q_time
        results_solr += interpreted.num_found

    except KeyboardInterrupt:
        break
    except UnicodeDecodeError:
        pass
