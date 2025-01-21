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

# This machine where the server runs has some important python dependencies
#   - twisted
#   - numpy
#   - sklearn (joblib)

from __future__ import absolute_import
from __future__ import print_function

from builtins import str
import json
import logging

import graypy
import tagrecommendation_settings as tr_settings
from tag_recommendation.community_tag_recommender import CommunityBasedTagRecommender
from concurrent_log_handler import ConcurrentRotatingFileHandler
from twisted.internet import reactor
from twisted.web import server, resource

from utils import loadFromJson, saveToJson


def server_interface(resource):
    return {
        'recommend_tags': resource.recommend_tags,  # input_tags (tags separated by commas), max_number_of_tags (optional)
        'reload': resource.reload,
        'last_indexed_id': resource.last_indexed_id,
        'add_to_index': resource.add_to_index,  # sound_ids (str separated by commas), sound_tagss (sets of tags separated by #)
    }


class TagRecommendationServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False

        self.load()

    def load(self):
        try:
            tag_recommendation_data = loadFromJson(
                tr_settings.RECOMMENDATION_DATA_DIR + 'Current_database_and_class_names.json')
            DATABASE = tag_recommendation_data['database']
            CLASSES = tag_recommendation_data['classes']
            self.cbtr = CommunityBasedTagRecommender(dataset=DATABASE, classes=CLASSES)
            self.cbtr.load_recommenders()

        except:
            self.cbtr = None
            logger.info("No computed matrices were found, recommendation system not loading for the moment ("
                        "but service listening for data to come).")

        try:
            self.index_stats = loadFromJson(
                tr_settings.RECOMMENDATION_DATA_DIR + 'Current_index_stats.json')
            logger.info("Matrices computed out of information from %i sounds" % self.index_stats['n_sounds_in_matrix'])
        except Exception as e:
            print(e)
            self.index_stats = {
                'n_sounds_in_matrix': 0,
            }

        try:
            self.index = loadFromJson(tr_settings.RECOMMENDATION_DATA_DIR, 'Index.json')
            self.index_stats['biggest_id_in_index'] = max([int(key) for key in self.index.keys()])
            self.index_stats['n_sounds_in_index'] = len(self.index.keys())
        except Exception as e:
            logger.info("Index file not present. Listening for indexing data from appservers.")
            self.index_stats['biggest_id_in_index'] = 0
            self.index_stats['n_sounds_in_index'] = 0
            self.index = dict()

    def error(self,message):
        return json.dumps({'Error': message})

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](**request.args)

    def recommend_tags(self, input_tags, max_number_of_tags=None):

        try:
            logger.info('Getting recommendation for input tags %s' % input_tags)
            input_tags = input_tags[0].split(",")
            if max_number_of_tags:
                max_number_of_tags = int(max_number_of_tags[0])
            recommended_tags, com_name = self.cbtr.recommend_tags(input_tags,
                                                                  max_number_of_tags=max_number_of_tags)
            result = {'error': False, 'result': {'tags': recommended_tags, 'community': com_name}}

        except Exception as e:
            logger.info('Errors occurred while recommending tags to %s' % input_tags)
            result = {'error': True, 'result': str(e)}

        return json.dumps(result)

    def reload(self):
        logger.info('Reloading tagrecommendation server...')
        self.load()
        result = {'error': False, 'result': "Server reloaded"}
        return json.dumps(result)

    def last_indexed_id(self):
        result = {'error': False, 'result': self.index_stats['biggest_id_in_index']}
        logger.info('Getting last indexed id information (%i, %i sounds in index, %i sounds in matrix)'
                    % (self.index_stats['biggest_id_in_index'],
                       self.index_stats['n_sounds_in_index'],
                       self.index_stats['n_sounds_in_matrix']))
        return json.dumps(result)

    def add_to_index(self, sound_ids, sound_tagss):
        sound_ids = sound_ids[0].split(",")
        sound_tags = [stags.split(",") for stags in sound_tagss[0].split("-!-!-")]
        logger.info('Adding %i sounds to recommendation index' % len(sound_ids))

        for count, sound_id in enumerate(sound_ids):
            sid = sound_id
            stags = sound_tags[count]
            self.index[sid] = stags

        if len(self.index.keys()) % 1000 == 0:
            # Every 1000 indexed sounds, save the index
            logger.info('Saving tagrecommendation index...')
            saveToJson(tr_settings.RECOMMENDATION_DATA_DIR + 'Index.json', self.index, verbose=False)
            self.index_stats['biggest_id_in_index'] = max([int(key) for key in self.index.keys()])
            self.index_stats['n_sounds_in_index'] = len(self.index.keys())

        result = {'error': False, 'result': True}
        return json.dumps(result)


if __name__ == '__main__':
    # Set up logging
    if not tr_settings.LOG_TO_STDOUT:
        print("LOG_TO_STDOUT is False, will not log")
    logger = logging.getLogger('tagrecommendation')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if tr_settings.LOG_TO_FILE:
        handler = ConcurrentRotatingFileHandler(
            tr_settings.LOGFILE, mode="a", maxBytes=2 * 1024 * 1024, backupCount=5,
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    if tr_settings.LOG_TO_STDOUT:
        std_handler = logging.StreamHandler()
        std_handler.setLevel(logging.DEBUG)
        std_handler.setFormatter(formatter)
        logger.addHandler(std_handler)
    if tr_settings.LOG_TO_GRAYLOG:
        handler_gelf = graypy.GELFUDPHandler(tr_settings.LOGSERVER_HOST, tr_settings.LOGSERVER_PORT)
        logger.addHandler(handler_gelf)

    # Start service
    logger.info('Configuring tag recommendation service...')
    root = resource.Resource()
    root.putChild("tagrecommendation", TagRecommendationServer())
    site = server.Site(root)
    reactor.listenTCP(tr_settings.LISTEN_PORT, site)
    logger.info('Started tag recommendation service, listening to port ' + str(tr_settings.LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')
