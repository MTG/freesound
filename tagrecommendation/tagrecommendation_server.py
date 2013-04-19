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
#   - sklearn
#   - pysparse

from twisted.web import server, resource
from twisted.internet import reactor
from tagrecommendation_settings import *
import logging
import graypy
from logging.handlers import RotatingFileHandler
import json
from communityBasedTagRecommendation import CommunityBasedTagRecommender


def server_interface(resource):
    return {
        'recommend_tags':resource.recommend_tags, # input_tags (tags separated by commas)
    }


class TagRecommendationServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False

        # Load tag recommender
        self.cbtr = CommunityBasedTagRecommender()
        self.cbtr.load_recommenders()

    def error(self,message):
        return json.dumps({'Error':message})

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](**request.args)

    def recommend_tags(self, input_tags):
        try:
            logger.debug('Getting recommendation for input tags %s' % input_tags)
            input_tags = input_tags[0].split(",")
            recommended_tags = self.cbtr.recommend_tags(input_tags, general_recommendation=True)
            result = {'error': False, 'result': recommended_tags}

        except Exception, e:
            logger.debug('Errors occurred while recommending tags to %s' % input_tags)
            result = {'error': True, 'result': str(e)}

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


