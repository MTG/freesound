#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#


import json
import logging

from django.core.management.base import BaseCommand
from django.db import connection
import networkx as nx

from sounds.models import Sound, RemixGroup

web_logger = logging.getLogger("web")


class Command(BaseCommand):
    args = ''
    help = 'Create the groups used for rendering the global remix page'

    def handle(self, *args, **options):
        web_logger.info("Starting to create remix grooups")

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

        # 3) Create nodes with dates and metadata
        dg = _create_nodes(dg)

        # 4) Find weakly connected components (single direction)
        subgraphs = nx.weakly_connected_components(dg)
        
        # 5) delete all remixgroup objects to recalculate
        RemixGroup.objects.all().delete()
        
        # 6) Loop through all connected graphs in the dataset and create the groups
        n_groups_created = 0
        for sg_nodes in subgraphs:
            sg = dg.subgraph(sg_nodes).copy()
            _create_and_save_remixgroup(sg, RemixGroup())
            n_groups_created += 1

        web_logger.info("Finished createing remix grooups (%i groups created)" % n_groups_created)


def _create_nodes(dg):
    for node in dg.nodes():
        sound = Sound.objects.get(id=node)
        dg.add_node(node, **{'date': sound.created,
                             'nodeName': sound.original_filename,
                             'username': sound.user.username,
                             'sound_url_mp3': sound.locations()['preview']['LQ']['mp3']['url'],
                             'sound_url_ogg': sound.locations()['preview']['LQ']['ogg']['url'],
                             'waveform_url': sound.locations()['display']['wave']['M']['url']})
    return dg


def _create_and_save_remixgroup(sg, remixgroup): 
    # print ' ========================================= '
    # add to list the subgraphs(connected components) with the extra data
    node_list = list(sg.nodes(data=True))
    # pp(node_list)

    # sort by date (holds all subgraph nodes sorted by date)
    # we need this since we go forward in time (source older than remix)
    node_list.sort(key=lambda x: x[1]['date']) # I think ['date'] is not necessary
    # print ' ========== SORTED NODE_LIST ========= '
    # pp(node_list)

    # dict with key=sound_id, value=index, nodeName=original_filename
    # in the previous sorted by date list
    # FIXME: no need for all this data, can be simple dict, key=value
    container = {val[0]: {'index': idx, 'nodeName': val[1]['nodeName']} for (idx, val) in enumerate(node_list)}
    # print ' ========== CONTAINER ========= '
    # pp(container)

    links = []
    remixgroup.save()   # need to save to have primary key before ManyToMany
    # FIXME: no idea why nx.weakly_connected_components(sg) return list in list...
    remixgroup.sounds.set(max(nx.weakly_connected_components(sg), key=len))

    for sound in remixgroup.sounds.all():
        sound.invalidate_template_caches()
        sound.mark_index_dirty(commit=True)

    remixgroup.group_size = len(node_list)
    # FIXME: seems like double work here, maybe convert container to list and sort?
    nodes = [{'id': val[0],
              'username': val[1]['username'],
              'nodeName': val[1]['nodeName'],
              'sound_url_mp3': val[1]['sound_url_mp3'],
              'sound_url_ogg': val[1]['sound_url_ogg'],
              'waveform_url': val[1]['waveform_url'],
              'group': 1} for (idx, val) in enumerate(node_list)]
    for line in nx.generate_adjlist(sg):
        # print line
        if len(line.split()) > 1:
            for i, l in enumerate(line.strip().split(" ")):
                # index 0 is the source, which we already know
                if i > 0:
                    link = {'target': container[int(line.split(" ")[0])]['index'],
                            'source': container[int(l)]['index']}
                    links.append(link)

    remixgroup.protovis_data = "{\"color\": \"#F1D9FF\"," \
                               "\"length\":" + str(len(node_list)) + "," \
                               "\"nodes\": " + json.dumps(nodes) + "," \
                               "\"links\": " + json.dumps(links) + "}"
                               
    remixgroup.networkx_data = json.dumps(dict(nodes=list(sg.nodes()), edges=list(sg.edges())))
    remixgroup.save()   
