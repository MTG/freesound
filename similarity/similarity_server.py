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

from __future__ import print_function
from __future__ import absolute_import
from twisted.web import server, resource
from twisted.internet import reactor
from .gaia_wrapper import GaiaWrapper
from .similarity_settings import LISTEN_PORT, LOGFILE, DEFAULT_PRESET, DEFAULT_NUMBER_OF_RESULTS, INDEX_NAME, PRESETS, \
    BAD_REQUEST_CODE, NOT_FOUND_CODE, SERVER_ERROR_CODE, LOGSERVER_IP_ADDRESS, LOGSERVER_PORT, LOG_TO_STDOUT, \
    LOG_TO_GRAYLOG, LOG_TO_FILE
import logging
import graypy
from logging.handlers import RotatingFileHandler
from .similarity_server_utils import parse_filter, parse_target, parse_metric_descriptors
import json
import yaml
import cloghandler


def server_interface(resource):
    return {
        'add_point': resource.add_point,  # location, sound_id
        'delete_point': resource.delete_point, # sound_id
        'get_all_point_names': resource.get_all_point_names,
        'get_descriptor_names': resource.get_descriptor_names,
        'contains': resource.contains,  # sound_id
        'get_sounds_descriptors': resource.get_sounds_descriptors,  # sound_ids, descritor_names (optional), normalization (optional)
        'nnsearch': resource.nnsearch,  # sound_id, num_results (optional), preset (optional)
        'api_search': resource.api_search,
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

    def get_all_point_names(self, request):
        return json.dumps(self.gaia.get_all_point_names())

    def get_descriptor_names(self, request):
        return json.dumps({'error': False, 'result': self.gaia.descriptor_names})

    def get_sounds_descriptors(self, request, sound_ids, descriptor_names=None, normalization=[0], only_leaf_descriptors=[0]):
        kwargs = dict()
        if descriptor_names:
            kwargs['descriptor_names'] = [name for name in descriptor_names[0].split(',') if name]
        kwargs['normalization'] = normalization[0] == '1'
        kwargs['only_leaf_descriptors'] = only_leaf_descriptors[0] == '1'
        return json.dumps(self.gaia.get_sounds_descriptors(sound_ids[0].split(','), **kwargs))

    def nnsearch(self, request, sound_id=None, num_results=None, preset=None, offset=[0]):

        preset = ['pca']  # For the moment we only admit pca preset, in the future we may allow more presets

        if not num_results:
            num_results = [DEFAULT_NUMBER_OF_RESULTS]

        return json.dumps(self.gaia.search_dataset(sound_id[0], num_results[0], preset_name=preset[0], offset=offset[0]))

    def api_search(self, request, target_type=None, target=None, filter=None, preset=[DEFAULT_PRESET], metric_descriptor_names=None, num_results=[DEFAULT_NUMBER_OF_RESULTS], offset=[0], in_ids=None):
        '''
        This function is used as an interface to all search-related gaia funcionalities we use in freesound.
        This function allows the definition of a query point that will be used by gaia as the target for the search (i.e.
        gaia will sort the results by similarity according to this point), and a filter to reduce the scope of the search.

        The query point is defined with the target and target_type parameters, and can be either a sound id from the
        gaia index, a list of descriptors with values or the content of a file attached to a post request.
            Ex:
                target=1234
                target_type=sound_id

                target=.lowlevel.pitch.mean:220
                target_type=descriptors_values

                target=.lowlevel.scvalleys.mean:-8.0,-11.0,-13.0,-15.0,-16.0,-15.0
                target_type=descriptors_values

        The filter is defined as a string following the same syntax as solr filter that is then parsed and translated to
        a representation that gaia can understand.
            Ex:
                filter=.lowlevel.pitch.mean:[100 TO *]
                TODO: how to filter multidimensional features

        Along with target and filter other parameters can be specified:
            - preset: set of descriptors that will be used to determine the similarity distance (by default 'lowlevel' preset)
            - metric_descriptor_names*: a list of descriptor names (separated by ,) that will be used as to build the distance metric (preset will be overwritten)
                * this parameter is bypassed with the descriptor_values target type, as the list is automatically built with the descriptors specified in the target
            - num_results, offset: to control the number of returned results and the offset since the first result (so pagination is possible)
        '''


        if in_ids:
            in_ids = in_ids[0].split(',')

        if not target and not filter:
            if target_type:
                if target_type[0] != 'file':
                    return json.dumps({'error': True, 'result': 'At least \'target\' or \'filter\' should be specified.', 'status_code': BAD_REQUEST_CODE})
            else:
                return json.dumps({'error': True, 'result': 'At least \'target\' or \'filter\' should be specified.', 'status_code': BAD_REQUEST_CODE})
        if target and not target_type:
            return json.dumps({'error': True, 'result': 'Parameter \'target_type\' should be specified.', 'status_code': BAD_REQUEST_CODE})
        if target_type:
            target_type = target_type[0]

        if target or target_type == 'file':
            if target_type == 'sound_id':
                try:
                    target = int(target[0])
                except:
                    return json.dumps({'error': True, 'result': 'Invalid sound id.', 'status_code': BAD_REQUEST_CODE})
            elif target_type == 'descriptor_values':
                try:
                    target = parse_target(target[0].replace("'", '"'), self.gaia.descriptor_names['fixed-length'])
                    if type(target) != dict:
                        if type(target) == str:
                            return json.dumps({'error': True, 'result': target, 'status_code': BAD_REQUEST_CODE})
                        else:
                            return json.dumps({'error': True, 'result': 'Invalid descriptor values for target.', 'status_code': BAD_REQUEST_CODE})
                    if not target.items():
                        return json.dumps({'error': True, 'result': 'Invalid target.', 'status_code': BAD_REQUEST_CODE})
                except Exception as e:
                    return json.dumps({'error': True, 'result': 'Invalid descriptor values for target.', 'status_code': BAD_REQUEST_CODE})
            elif target_type == 'file':
                data = request.content.getvalue().split('&')[0]  # If more than one file attached, just get the first one
                if not data:
                    return json.dumps({'error': True, 'result': 'You specified \'file\' as target file but attached no analysis file.', 'status_code': BAD_REQUEST_CODE})
                try:
                    target = yaml.safe_load(data)
                except:
                    return json.dumps({'error': True, 'result': 'Analysis file could not be parsed.', 'status_code': BAD_REQUEST_CODE})
            else:
                return json.dumps({'error': True, 'result': 'Invalid target type.', 'status_code': BAD_REQUEST_CODE})

        if filter:
            try:
                filter = parse_filter(filter[0].replace("'", '"'), self.gaia.descriptor_names['fixed-length'])
                if type(filter) != list:
                    if type(filter) == str:
                        return json.dumps({'error': True, 'result': filter, 'status_code': BAD_REQUEST_CODE})
                    else:
                        return json.dumps({'error': True, 'result': 'Invalid filter.', 'status_code': BAD_REQUEST_CODE})
            except Exception as e:
                return json.dumps({'error': True, 'result': 'Invalid filter.', 'status_code': BAD_REQUEST_CODE})

        '''
        if preset:
            if preset[0] not in PRESETS:
                preset = DEFAULT_PRESET
            else:
                preset = preset[0]
        '''
        preset = 'pca'  # For the moment we only admit pca preset, in the future we may allow more presets

        if not num_results[0]:
            num_results = int(DEFAULT_NUMBER_OF_RESULTS)
        else:
            num_results = int(num_results[0])

        if not offset[0]:
            offset = 0
        else:
            offset = int(offset[0])

        if target_type == 'descriptor_values' and target:
            metric_descriptor_names = parse_metric_descriptors(','.join(target.keys()), self.gaia.descriptor_names['fixed-length'])
        else:
            metric_descriptor_names = False  # For the moment metric_descriptor_names can only be set by us

        return json.dumps(self.gaia.api_search(target_type,
                                              target,
                                              filter,
                                              preset,
                                              metric_descriptor_names,
                                              num_results,
                                              offset,
                                              in_ids))


    def save(self, request, filename=None):
        if not filename:
            filename = [INDEX_NAME]

        return json.dumps(self.gaia.save_index(filename[0]))


if __name__ == '__main__':
    # Set up logging
    if not LOG_TO_STDOUT:
        print("LOG_TO_STDOUT is False, will not log")
    logger = logging.getLogger('similarity')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    if LOG_TO_FILE:
        handler = cloghandler.ConcurrentRotatingFileHandler(LOGFILE, "a", maxBytes=2*1024*1024, backupCount=5)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    if LOG_TO_STDOUT:
        std_handler = logging.StreamHandler()
        std_handler.setLevel(logging.DEBUG)
        std_handler.setFormatter(formatter)
        logger.addHandler(std_handler)
    if LOG_TO_GRAYLOG:
        handler_graypy = graypy.GELFHandler(LOGSERVER_IP_ADDRESS, LOGSERVER_PORT)
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
