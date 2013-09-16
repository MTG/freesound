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


from twisted.web import server, resource
from twisted.internet import reactor
from tagrecommendation_settings import *
import logging
import graypy
from logging.handlers import RotatingFileHandler
import json
from communityBasedTagRecommendation import CommunityBasedTagRecommender
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

        # Load tag recommender
        try:
            tag_recommendation_data = loadFromJson(RECOMMENDATION_DATA_DIR + 'Current_database_and_class_names.json')
            DATABASE = tag_recommendation_data['database']
            CLASSES = tag_recommendation_data['classes']
            self.cbtr = CommunityBasedTagRecommender(dataset=DATABASE, classes=CLASSES)
            self.cbtr.load_recommenders()

        except:
            self.cbtr = None
            logger.info("No computed matrices were found, recommendation system not loading for the moment (but service listening for data to come).")

        try:
            self.index_stats = loadFromJson(RECOMMENDATION_DATA_DIR + 'Current_index_stats.json')
            logger.info("Matrices computed out of information from %i sounds" % self.index_stats['n_sounds_in_matrix'])
        except Exception, e:
            self.index_stats = {
                'n_sounds_in_matrix': 0,
            }

        try:
            index = loadFromJson(RECOMMENDATION_DATA_DIR + 'Index.json')
            self.index_stats['biggest_id_in_index'] = max([int(key) for key in index.keys()])
        except:
            logger.info("Index file not present. Listening for indexing data from appservers.")
            self.index_stats['biggest_id_in_index'] = 0

    def error(self,message):
        return json.dumps({'Error': message})

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](**request.args)

    def recommend_tags(self, input_tags, max_number_of_tags=None):

        try:
            logger.debug('Getting recommendation for input tags %s' % input_tags)
            input_tags = input_tags[0].split(",")
            if max_number_of_tags:
                max_number_of_tags = int(max_number_of_tags[0])
            recommended_tags, com_name = self.cbtr.recommend_tags(input_tags,
                                                                  max_number_of_tags=max_number_of_tags)
            result = {'error': False, 'result': {'tags': recommended_tags, 'community': com_name}}

        except Exception, e:
            logger.debug('Errors occurred while recommending tags to %s' % input_tags)
            result = {'error': True, 'result': str(e)}

        return json.dumps(result)

    def reload(self):
        # Load tag recommender
        try:
            tag_recommendation_data = loadFromJson(RECOMMENDATION_DATA_DIR + 'Current_database_and_class_names.json')
            DATABASE = tag_recommendation_data['database']
            CLASSES = tag_recommendation_data['classes']
            self.index_stats = loadFromJson(RECOMMENDATION_DATA_DIR + 'Current_index_stats.json')
        except Exception, e:
            raise Exception("No metadata found for computed matrixs. Tag recommendation system can not start.")

        self.cbtr = None
        try:

            self.cbtr = CommunityBasedTagRecommender(dataset=DATABASE, classes=CLASSES)
            self.cbtr.load_recommenders()
            result = {'error': False, 'result': "Server reloaded"}
        except Exception, e:
            result = {'error': True, 'result': str(e)}

        return json.dumps(result)

    def last_indexed_id(self):
        result = {'error': False, 'result': self.index_stats['biggest_id_in_index']}
        return json.dumps(result)

    def add_to_index(self, sound_ids, sound_tagss):
        sound_ids = sound_ids[0].split(",")
        sound_tags = [stags.split(",") for stags in sound_tagss[0].split("-!-!-")]
        logger.info('Adding %i sounds to recommendation index' % len(sound_ids))

        try:
            index = loadFromJson(RECOMMENDATION_DATA_DIR + 'Index.json')
        except Exception, e:
            index = dict()

        for count, sound_id in enumerate(sound_ids):
            sid = sound_id
            stags = sound_tags[count]
            index[sid] = stags

        saveToJson(RECOMMENDATION_DATA_DIR + 'Index.json', index, verbose=False)

        result = {'error': False, 'result': True}
        return json.dumps(result)


if __name__ == '__main__':
    # Set up logging
    logger = logging.getLogger('tagrecommendation')
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(LOGFILE, maxBytes=2*1024*1024, backupCount=5)
    handler.setLevel(logging.DEBUG)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    std_handler.setFormatter(formatter)
    logger.addHandler(std_handler)
    handler_graypy = graypy.GELFHandler('10.55.0.48', 12201)
    logger.addHandler(handler_graypy)

    # Start service
    logger.info('Configuring tag recommendation service...')
    root = resource.Resource()
    root.putChild("tagrecommendation", TagRecommendationServer())
    site = server.Site(root)
    reactor.listenTCP(LISTEN_PORT, site)
    logger.info('Started tag recommendation service, listening to port ' + str(LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')


