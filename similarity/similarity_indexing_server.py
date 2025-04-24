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


'''
The similarity indexing server is a simpler version of the similarity server which can only handle indexing sounds.
This server can be used to index a new dataset in background so when it is indexed the main similarity service
can be reloaded with the new index.
'''

from __future__ import absolute_import

from builtins import str
import json
import logging
from logging.handlers import RotatingFileHandler

import graypy
from twisted.internet import reactor
from twisted.web import server, resource

from .gaia_wrapper import GaiaWrapper
from . import similarity_settings as sim_settings


def server_interface(resource):
    return {
        'add_point': resource.add_point,  # location, sound_id
        'clear_memory': resource.clear_memory,
        'reload_gaia_wrapper': resource.reload_gaia_wrapper,
        'save': resource.save,  # filename (optional)
    }

class SimilarityServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False
        self.gaia = GaiaWrapper(indexing_only_mode=True)
        self.request = None

    def error(self,message):
        return json.dumps({'Error': message})

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](request=request, **request.args)

    def add_point(self, request, location, sound_id):
        return json.dumps( self.gaia.add_point(location[0],sound_id[0]))

    def save(self, request, filename=None):
        if not filename:
            filename = [sim_settings.INDEXING_SERVER_INDEX_NAME]
        return json.dumps(self.gaia.save_index(filename[0]))

    def reload_gaia_wrapper(self, request):
        self.gaia = GaiaWrapper(indexing_only_mode=True)
        return json.dumps({'error': False, 'result': 'Gaia wrapper reloaded!'})

    def clear_memory(self, request):
        # Then clear the memory
        return json.dumps(self.gaia.clear_index_memory())


if __name__ == '__main__':
    # Set up logging
    logger = logging.getLogger('similarity')
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(sim_settings.LOGFILE_INDEXING_SERVER, maxBytes=2 * 1024 * 1024, backupCount=5)
    handler.setLevel(logging.DEBUG)
    std_handler = logging.StreamHandler()
    std_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    std_handler.setFormatter(formatter)
    logger.addHandler(std_handler)
    handler_gelf = graypy.GELFUDPHandler(sim_settings.LOGSERVER_HOST, sim_settings.LOGSERVER_PORT)
    logger.addHandler(handler_gelf)

    # Start service
    logger.info('Configuring similarity INDEXING service...')
    root = resource.Resource()
    root.putChild("similarity", SimilarityServer())
    site = server.Site(root)
    reactor.listenTCP(sim_settings.INDEXING_SERVER_LISTEN_PORT, site)
    logger.info('Started similarity INDEXING service, listening to port ' + str(
        sim_settings.INDEXING_SERVER_LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')
