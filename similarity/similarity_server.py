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

from twisted.web import server, resource
from twisted.internet import reactor
from gaia_wrapper import GaiaWrapper
from similarity_settings import LISTEN_PORT, LOGFILE, DEFAULT_PRESET, DEFAULT_NUMBER_OF_RESULTS, INDEX_NAME, PRESETS
import logging
import graypy
from logging.handlers import RotatingFileHandler
from similarity_server_utils import parse_filter, parse_target
import json
import yaml


def server_interface(resource):
    return {
        'add_point': resource.add_point,  # location, sound_id
        'delete_point': resource.delete_point, # sound_id
        'contains': resource.contains,  # sound_id
        'get_sounds_descriptors': resource.get_sounds_descriptors,  # sound_ids, descritor_names (optional), normalization (optional)
        'nnsearch': resource.nnsearch,  # sound_id, num_results (optional), preset (optional)
        'nnrange': resource.nnrange,  # target, filter, num_results (optional), preset (optional)
        'save': resource.save,  # filename (optional)
    }


class SimilarityServer(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.methods = server_interface(self)
        self.isLeaf = False
        self.gaia = GaiaWrapper()
        self.request = None

    def error(self,message):
        return json.dumps({'Error':message})

    def getChild(self, name, request):
        return self

    def render_GET(self, request):
        return self.methods[request.prepath[1]](request=request, **request.args)

    def render_POST(self, request):
        return self.methods[request.prepath[1]](request=request, **request.args)

    def add_point(self, request, location, sound_id):
        return json.dumps( self.gaia.add_point(location[0],sound_id[0]))

    def delete_point(self, request, sound_id):
        return json.dumps(self.gaia.delete_point(sound_id[0]))

    def contains(self, request, sound_id):
        return json.dumps(self.gaia.contains(sound_id[0]))

    def get_sounds_descriptors(self, request, sound_ids, descriptor_names=None, normalization=[0], only_leaf_descriptors=[0]):
        kwargs = dict()
        if descriptor_names:
            kwargs['descriptor_names'] = descriptor_names[0].split(',')
        kwargs['normalization'] = normalization[0] == '1'
        kwargs['only_leaf_descriptors'] = only_leaf_descriptors[0] == '1'
        return json.dumps(self.gaia.get_sounds_descriptors(sound_ids[0].split(','), **kwargs))

    def nnsearch(self, request, sound_id=None, num_results=None, preset=None, offset=[0]):
        descriptors_data = None
        if not sound_id:
            # Check if attached file
            data = request.content.getvalue().split('&')[0]  # If more than one file attached, just get the first one
            if not data:
                return json.dumps({'error': True, 'result': 'Either specify a point id or attach an analysis file.'})

            # If not sound id but file attached found, parse file and pass as a dict
            sound_id = [None]
            try:
                descriptors_data = yaml.load(data)
            except:
                return json.dumps({'error': True, 'result': 'Analysis file could not be parsed.'})

        if not preset:
            preset = [DEFAULT_PRESET]
        else:
            if preset[0] not in PRESETS:
                preset = [DEFAULT_PRESET]
        if not num_results:
            num_results = [DEFAULT_NUMBER_OF_RESULTS]

        return json.dumps(self.gaia.search_dataset(sound_id[0], num_results[0], preset_name=preset[0], offset=offset[0], descriptors_data=descriptors_data))

    def nnrange(self, request, target=None, filter=None, num_results=None, offset=[0], preset=None):
        descriptors_data = None
        if not filter:
            if not target:
                # check if instead of a target, an analysis file was attached
                data = request.content.getvalue().split('&')[0]  # If more than one file attached, just get the first one
                if not data:
                    return json.dumps({'error': True, 'result': 'You should at least specify a descriptors_filter, descriptors_target or attach an analysis file for content based search.'})
                try:
                    descriptors_data = yaml.load(data)
                except:
                    return json.dumps({'error': True, 'result': 'Analysis file could not be parsed.'})

        if not num_results:
            num_results = [DEFAULT_NUMBER_OF_RESULTS]
        if not preset:
            preset = [DEFAULT_PRESET]
        else:
            if preset[0] not in PRESETS:
                preset = [DEFAULT_PRESET]

        if filter:
            filter = filter[0]
            pf = parse_filter(filter.replace("'",'"'))
        else:
            pf = []

        target_sound_id = False
        use_file_as_target = False
        if target:
            target = target[0]
            try:
                # If target can be parsed as an integer, we assume it corresponds to a sound_id
                target_sound_id = int(target)
                pt = {}
            except:
                pt = parse_target(target.replace("'",'"'))
        else:
            pt = {}
            if descriptors_data:
                use_file_as_target = True

        if type(pf) != list or type(pt) != dict:
            message = ""
            if type(pf) == str:
                message += pf
            if type(pt) == str:
                message += pt
            if message == "":
                message = "Invalid filter or target."

            return json.dumps({'error': True, 'result': message})


        return json.dumps(self.gaia.query_dataset({'target': pt, 'filter': pf},
                                                  num_results[0],
                                                  preset_name=preset[0],
                                                  offset=offset[0],
                                                  target_sound_id=target_sound_id,
                                                  use_file_as_target=use_file_as_target,
                                                  descriptors_data=descriptors_data))

    def save(self, request, filename=None):
        if not filename:
            filename = [INDEX_NAME]

        return json.dumps(self.gaia.save_index(filename[0]))


if __name__ == '__main__':
    # Set up logging
    logger = logging.getLogger('similarity')
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
    logger.info('Configuring similarity service...')
    root = resource.Resource()
    root.putChild("similarity", SimilarityServer())
    site = server.Site(root)
    reactor.listenTCP(LISTEN_PORT, site)
    logger.info('Started similarity service, listening to port ' + str(LISTEN_PORT) + "...")
    reactor.run()
    logger.info('Service stopped.')


