'''
Created on Jun 1, 2011

@author: stelios
'''
from __future__ import division
from django.core.management.base import BaseCommand
from django.db import connection
from networkx import nx
from pprint import pprint as pp
from sounds.models import Sound, RemixGroup
import json

# TODO: 1) test me!!! if sound not found in more than 1 groups we should be OK
#       2) save to RemixGroup model
#       3) group number?
class Command(BaseCommand):
    args = ''
    help = 'Create the groups used for rendering the global remix page'

    def handle(self, *args, **options):
        # 1) Get all the sounds that have remixes
        cursor = connection.cursor()
        cursor.execute("""
                        SELECT
                            src.from_sound_id AS from,
                            src.to_sound_id AS to,
                            snd.created AS created
                        FROM
                            sounds_sound_sources src,
                            sounds_sound snd
                        WHERE
                            src.to_sound_id = snd.id
                        ORDER BY
                            snd.created ASC
                        """)

        # 2) Create directed graph
        dg = nx.DiGraph()
        for row in cursor:
            dg.add_edge(row[0], row[1])

        # 3) Add date to nodes for sorting (FIXME: how can we avoid this query???)
        """
        for node in dg.nodes():
            cursor.execute("SELECT snd.created, snd.original_filename, au.username " \
                           "FROM sounds_sound snd, auth_user au WHERE au.id=snd.user_id AND snd.id = %s", [node])
            temp = cursor.fetchone()
            dg.add_node(node, {'date':temp[0],
                               'nodeName': temp[1],
                               'username': temp[2]})
        """
        for node in dg.nodes():
            sound = Sound.objects.get(id=node)
            dg.add_node(node, {'date': sound.created,
                               'nodeName': sound.original_filename,
                               'username': sound.user.username,
                               'sound_url_mp3': sound.locations()['preview']['LQ']['mp3']['url'],
                               'sound_url_ogg': sound.locations()['preview']['LQ']['ogg']['url'],
                               'waveform_url': sound.locations()['display']['wave']['M']['url']})
        
        # print dg.nodes(data=True)
        # 4) Find weakly connected components (single direction)
        subgraphs = nx.weakly_connected_component_subgraphs(dg)
        node_list = []
        # 5) delete all remixgroup objects to recalculate
        RemixGroup.objects.all().delete()
        # 6) Loop through all connected graphs in the dataset
        #    and create the groups
        for sg_idx,sg in enumerate(subgraphs):
            remixgroup = RemixGroup()
            # print ' ========================================= '
            # add to list the subgraphs(connected components) with the extra data
            node_list = sg.nodes(data=True)
            # pp(node_list)

            # sort by date (holds all subgraph nodes sorted by date)
            # we need this since we go forward in time (source older than remix)
            node_list.sort(key = lambda x: x[1]['date']) # I think ['date'] is not necessary
            # print ' ========== SORTED NODE_LIST ========= '
            # pp(node_list)

            # dict with key=sound_id, value=index, nodeName=original_filname
            # in the previous sorted by date list
            # FIXME: no need for all this data, can be simple dict, key=value
            container = dict((val[0],{'index': idx, 'nodeName': val[1]['nodeName']}) for (idx,val) in enumerate(node_list))
            # print ' ========== CONTAINER ========= '
            # pp(container)

            links = []
            remixgroup.save()   # need to save to have primary key before ManyToMany
            # FIXME: no idea why nx.weakly_connected_components(sg) return list in list...
            remixgroup.sounds = set(nx.weakly_connected_components(sg)[0])
            remixgroup.group_size = len(node_list)
            # FIXME: seems like double work here, maybe convert container to list and sort?
            nodes = [{'id': val[0],
                      'username': val[1]['username'],
                      'nodeName': val[1]['nodeName'],
                      'sound_url_mp3': val[1]['sound_url_mp3'],
                      'sound_url_ogg': val[1]['sound_url_ogg'],
                      'waveform_url': val[1]['waveform_url'],
                      'group': 1} for (idx,val) in enumerate(node_list)]
            for line in nx.generate_adjlist(sg):
                # print line
                if len(line.split()) > 1:
                    for i,l in enumerate(line.strip().split(" ")):
                        # index 0 is the source, which we already know
                        if i > 0:
                            link = {'target': container[int(line.split(" ")[0])]['index'],
                                    'source': container[int(l)]['index']}
                            links.append(link)
                            #print link
            remixgroup.protovis_data = "{\"color\": \"#F1D9FF\"," \
                                       "\"length\":" + str(len(node_list)) + "," \
                                       "\"nodes\": " + json.dumps(nodes) + "," \
                                       "\"links\": " + json.dumps(links) + "}"
            remixgroup.save()

            """
            print ' ========== NODES ========='
            pp(nodes)
            print ' ========== LINKS ========='
            pp(links)
            """
