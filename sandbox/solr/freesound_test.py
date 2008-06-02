import time
from solr import *

"""An example of usage, with the freesound custom schema...
"""

solr = Solr("http://localhost:8983/solr/", persistent=True)

num_queries_total = 0
num_queries_this_loop = 0

time_solr = 0

start = time.time()
start_this_loop = start

for index, line in enumerate(file("searches")):
    if index % 200 == 0 and index > 0:
        avg_total = ((time.time() - start_this_loop) * 1000) / float(num_queries_this_loop)
        avg_solr = time_solr / float(num_queries_this_loop)
        avg_python = avg_total - avg_solr
        
        print "Batch of", num_queries_this_loop, "queries. Total queries:", num_queries_total
        print "\tAverage total time:", avg_total
        print "\tAverage solr:", avg_solr
        print "\tAverage python:", avg_python

        num_queries_this_loop = 0
        time_solr = 0
        start_this_loop = time.time()
                        
    try:
        (search, count) = line.strip().split("\t")
        count = int(count)
        search = search.replace("--", "")
        
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

    except KeyboardInterrupt:
        break
    except UnicodeDecodeError:
        pass
    except Exception, e:
        print e, type(e)
        break