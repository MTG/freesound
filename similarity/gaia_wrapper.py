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

import os, logging, yaml
from gaia2 import DataSet, transform, DistanceFunctionFactory, View, Point
from similarity_settings import SIMILARITY_MINIMUM_POINTS, INDEX_DIR, DEFAULT_PRESET, PRESETS, PRESET_DIR, INDEX_NAME
from similarity_server_utils import generate_structured_dict_from_layout, get_nested_dictionary_value, get_nested_descriptor_names, set_nested_dictionary_value
import time

logger = logging.getLogger('similarity')

class GaiaWrapper:

    def __init__(self):
        self.index_path                 = INDEX_DIR
        self.original_dataset           = DataSet()
        self.original_dataset_path      = self.__get_dataset_path(INDEX_NAME)
        self.metrics                    = {}
        self.view                       = None
        self.__load_dataset()


    def __get_dataset_path(self, ds_name):
        return os.path.join(INDEX_DIR, ds_name + '.db')


    def __load_dataset(self):
        # Loads the dataset, applies transforms if needed and saves. If dataset does not exists, creates an empty one and saves.

        if not os.path.exists(INDEX_DIR):
            os.makedirs(INDEX_DIR)

        # load original dataset
        if os.path.exists(self.original_dataset_path):
            self.original_dataset.load(self.original_dataset_path)
            if self.original_dataset.size() >= SIMILARITY_MINIMUM_POINTS:

                # if we have loaded a dataset of the correct size but it is unprepared, prepare it
                if self.original_dataset.history().size() <= 0:
                    self.__prepare_original_dataset()
                    self.__normalize_original_dataset()
                    self.original_dataset.save(self.original_dataset_path)

                # if we have loaded a dataset which has not been normalized, normalize it
                normalized = False
                for element in self.original_dataset.history().toPython():
                    if element['Analyzer name'] == 'normalize':
                        normalized = True
                        break
                if not normalized:
                    self.__normalize_original_dataset()
                    self.original_dataset.save(self.original_dataset_path)

                # build metrics for the different similarity presets
                self.__build_metrics()
                # create view
                view = View(self.original_dataset)
                self.view = view

            logger.debug('Dataset loaded, size: %s points' % (self.original_dataset.size()))

        else:
            # If there is no existing dataset we create an empty one.
            # For the moment we do not create any distance metric nor a view because search won't be possible until the DB has a minimum of SIMILARITY_MINIMUM_POINTS
            self.original_dataset.save(self.original_dataset_path)
            logger.debug('Created new dataset, size: %s points (should be 0)' % (self.original_dataset.size()))


    def __prepare_original_dataset(self):
        logger.debug('Preparing the original dataset.')
        self.original_dataset = self.prepare_original_dataset_helper(self.original_dataset)

    def __normalize_original_dataset(self):
        logger.debug('Normalizing the original dataset.')
        self.original_dataset = self.normalize_dataset_helper(self.original_dataset)

    @staticmethod
    def prepare_original_dataset_helper(ds):
        proc_ds1  = transform(ds, 'RemoveVL')
        proc_ds2  = transform(proc_ds1,  'FixLength')
        proc_ds1 = None
        prepared_ds = transform(proc_ds2, 'Cleaner')
        proc_ds2 = None

        return prepared_ds

    @staticmethod
    def normalize_dataset_helper(ds):
        # Add normalization
        normalization_params = { "descriptorNames":"*","independent":True, "outliers":-1}
        normalized_ds = transform(ds, 'normalize', normalization_params)
        ds = None

        return normalized_ds

    def __build_metrics(self):
        for preset in PRESETS:
            logger.debug('Bulding metric for preset %s' % preset)
            name = preset
            path = PRESET_DIR + name + ".yaml"
            preset_file = yaml.load(open(path))
            distance = preset_file['distance']['type']
            parameters = preset_file['distance']['parameters']
            search_metric = DistanceFunctionFactory.create(str(distance),self.original_dataset.layout(),parameters)
            self.metrics[name] = search_metric


    def add_point(self, point_location, point_name):
        if self.original_dataset.contains(str(point_name)):
                self.original_dataset.removePoint(str(point_name))
        try:
            p = Point()
            p.load(str(point_location))
            p.setName(str(point_name))
            self.original_dataset.addPoint(p)
            size = self.original_dataset.size()
            logger.debug('Added point with name %s. Index has now %i points.' % (str(point_name),size))
        except:
            msg = 'Point with name %s could NOT be added. Index has now %i points.' % (str(point_name),size)
            logger.debug(msg)
            return {'error':True, 'result':msg}

        # If when adding a new point we reach the minimum points for similarity, prepare the dataset, save and create view and distance metrics
        #   This will most never happen, only the first time we start similarity server, there is no index created and we add 2000 points.
        if size == SIMILARITY_MINIMUM_POINTS:
            self.__prepare_original_dataset()
            self.__normalize_original_dataset()
            self.save_index(msg = "(reaching 2000 points)")

            # build metrics for the different similarity presets
            self.__build_metrics()
            # create view
            view = View(self.original_dataset)
            self.view = view

        return {'error':False, 'result':True}

    def delete_point(self, point_name):
        if self.original_dataset.contains(str(point_name)):
            self.original_dataset.removePoint(str(point_name))
            logger.debug('Deleted point with name %s. Index has now %i points.' % (str(point_name),self.original_dataset.size()))
            return {'error':False, 'result':True}
        else:
            msg = 'Can\'t delete point with name %s because it does not exist.'% str(point_name)
            logger.debug(msg)
            return {'error':True,'result':msg}

    def get_point(self, point_name):
        logger.debug('Getting point with name %s' % str(point_name))
        if self.original_dataset.contains(str(point_name)):
            return self.original_dataset.point(str(point_name))


    def save_index(self, filename = None, msg = ""):
        tic = time.time()
        path = self.original_dataset_path
        if filename:
            path =  INDEX_DIR + filename + ".db"
        logger.debug('Saving index to (%s)...'%path + msg)
        self.original_dataset.save(path)
        toc = time.time()
        logger.debug('Finished saving index (done in %.2f seconds, index has now %i points).'%((toc - tic),self.original_dataset.size()))
        return {'error':False,'result':path}


    def contains(self, point_name):
        logger.debug('Checking if index has point with name %s' % str(point_name))
        return {'error':False,'result':self.original_dataset.contains(point_name)}


    def get_sound_descriptors(self, point_name, descriptor_names=None, normalization=True):
        '''
        Given a point name it returns the values for the descriptors specified in 'descriptor_names' list.
        If no normalization coefficients are provided, the method will return normalized values [0-1].
        '''

        # We first process the descritor names to create the FULL list of descritors needed (ex: if
        # descriptor names include 'lowlevel.spectral_centroid', the output will include all statistics
        # on that descritor (lowlevel.spectral_cetroid.mean, lowlevel.spectral_cetroid.var...)
        required_descriptor_names = self.__calculate_complete_required_descriptor_names(descriptor_names)

        # Now we fill the required layout data structure with descritor values
        data = self.__get_point_descriptors(point_name, required_descriptor_names, normalization)
        if 'error' not in data:
            return {'error': False, 'result': data}
        else:
            return data


    def get_sounds_descriptors(self, point_names, descriptor_names=None, normalization=True):
        '''
        Returns a list with the descritor values for all requested point names
        '''
        data = dict()
        required_descriptor_names = self.__calculate_complete_required_descriptor_names(descriptor_names)
        for point_name in point_names:
            sound_descriptors = self.__get_point_descriptors(point_name, required_descriptor_names, normalization)
            if 'error' not in sound_descriptors:
                data[point_name] = sound_descriptors

        return {'error': False, 'result': data}


    def __calculate_complete_required_descriptor_names(self, descriptor_names):
        layout = self.original_dataset.layout()
        if not descriptor_names:
            descriptor_names = layout.descriptorNames()
        try:
            structured_layout = generate_structured_dict_from_layout(layout.descriptorNames())
            processed_descriptor_names = []
            for name in descriptor_names:
                nested_descriptors = get_nested_dictionary_value(name.split('.')[1:], structured_layout)
                if not nested_descriptors:
                    processed_descriptor_names.append(name)
                else:
                    # Return all nested descriptor names
                    extra_names = []
                    get_nested_descriptor_names(nested_descriptors, extra_names)
                    for extra_name in extra_names:
                        processed_descriptor_names.append('%s.%s' % (name, extra_name))
            processed_descriptor_names = list(set(processed_descriptor_names))
            return processed_descriptor_names

        except:
            return {'error': True, 'result': 'Wrong descriptor names, unable to create layout.'}


    def __get_point_descriptors(self, point_name, required_descriptor_names, normalization=True):
        # Get normalization coefficients to transform the input data (get info from the last
        # transformation which has been a normalization)

        normalization_coeffs = None
        if normalization:
            trans_hist = self.original_dataset.history().toPython()
            for i in range(0,len(trans_hist)):
                if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                    normalization_coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        required_layout = generate_structured_dict_from_layout(required_descriptor_names)
        try:
            p = self.original_dataset.point(str(point_name))
        except:
            return {'error': True, 'result': 'Sound does not exist in gaia index.'}

        for descriptor_name in required_descriptor_names:
            try:
                value = p.value(str(descriptor_name))
                if normalization_coeffs:
                    a = normalization_coeffs[descriptor_name]['a']
                    b = normalization_coeffs[descriptor_name]['b']
                    if len(a) == 1:
                        value = float(value - b[0]) / a[0]
                    else:
                        normalized_value = []
                        for i in range(0, len(a)):
                            normalized_value.append(float(value[i]-b[i]) / a[i])
                        value = normalized_value
            except:
                value = 'unknown'

            if descriptor_name[0] == '.':
                descriptor_name = descriptor_name[1:]
            set_nested_dictionary_value(descriptor_name.split('.'), required_layout, value)
        return required_layout


    # SIMILARITY SEARCH (WEB and API)
    def search_dataset(self, query_point, number_of_results, preset_name):
        preset_name = str(preset_name)
        query_point = str(query_point)
        logger.debug('NN search for point with name %s (preset = %s)' % (query_point,preset_name))
        size = self.original_dataset.size()
        if size < SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS)
            logger.debug(msg)
            return {'error':True,'result':msg}
            #raise Exception('Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS))

        if query_point.endswith('.yaml'):
            #The point doesn't exist in the dataset....
            # So, make a temporary point, add all the transformations
            # to it and search for it
            p, p1 = Point(), Point()
            p.load(query_point)
            p1 = self.original_dataset.history().mapPoint(p)
            similar_sounds = self.view.nnSearch(p1, self.metrics[preset_name]).get(int(number_of_results))
        else:
            if not self.original_dataset.contains(query_point):
                msg = "Sound with id %s doesn't exist in the dataset." % query_point
                logger.debug(msg)
                return {'error':True,'result':msg}
                #raise Exception("Sound with id %s doesn't exist in the dataset." % query_point)

            similar_sounds = self.view.nnSearch(query_point, self.metrics[preset_name]).get(int(number_of_results))

        return {'error':False, 'result':similar_sounds}


    # CONTENT-BASED SEARCH (API)
    def query_dataset(self, query_parameters, number_of_results):

        size = self.original_dataset.size()
        if size < SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS)
            logger.debug(msg)
            return {'error':True,'result':msg}
            #raise Exception('Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS))

        trans_hist = self.original_dataset.history().toPython()
        layout = self.original_dataset.layout()

        # Get normalization coefficients to transform the input data (get info from the last transformation which has been a normalization)
        coeffs = None
        for i in range(0,len(trans_hist)):
            if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        ##############
        # PARSE TARGET
        ##############

        # Transform input params to the normalized feature space and add them to a query point
        # If there are no params specified in the target, the point is set as empty (probably random sounds are returned)
        q = Point()
        q.setLayout(layout)
        feature_names = []
        # If some target has been specified...
        if query_parameters['target'].keys():
            for param in query_parameters['target'].keys():
                # Only add numerical parameters. Non numerical ones (like key) are only used as filters
                if param in coeffs.keys():
                    feature_names.append(str(param))
                    value = query_parameters['target'][param]
                    if coeffs:
                        a = coeffs[param]['a']
                        b = coeffs[param]['b']
                        if len(a) == 1:
                            norm_value = a[0]*value + b[0]
                        else:
                            norm_value = []
                            for i in range(0,len(a)):
                                norm_value.append(a[i]*value[i]+b[i])
                        #text = str(type(param)) + " " + str(type(norm_value))
                        q.setValue(str(param), norm_value)
                    else:
                        q.setValue(str(param), value)

        ##############
        # PARSE FILTER
        ##############

        filter = ""
        # If some filter has been specified...
        if query_parameters['filter']:
            if type(query_parameters['filter'][0:5]) == str:
                filter = query_parameters['filter']
            else:
                filter = self.parse_filter_list(query_parameters['filter'], coeffs)


        #############
        # DO QUERY!!!
        #############

        logger.debug("Content based search with target: " + str(query_parameters['target']) + " and filter: " + str(filter) )
        metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': feature_names})
        # Looks like that depending on the version of gaia, variable filter must go after or before the metric
	    # For the gaia version we have currently (sep 2012) in freesound: nnSearch(query,filter,metric)
        #results = self.view.nnSearch(q,str(filter),metric).get(int(number_of_results)) # <- Freesound
        results = self.view.nnSearch(q,metric,str(filter)).get(int(number_of_results))

        return {'error':False, 'result':results}


    # UTILS for content-based search
    def prepend_value_label(self, f):
        if f['type'] == 'NUMBER' or f['type'] == 'RANGE' or f['type'] == 'ARRAY':
            return "value"
        else:
            return "label"


    def parse_filter_list(self, filter_list, coeffs):

        # TODO: eliminate this?
        #coeffs = None

        filter = "WHERE"
        for f in filter_list:
            if type(f) != dict:
                filter += f
            else:
                if f['type'] == 'NUMBER' or f['type'] == 'STRING' or f['type'] == 'ARRAY':

                    if f['type'] == 'NUMBER':
                        if coeffs:
                            norm_value = coeffs[f['feature']]['a'][0] * f['value'] + coeffs[f['feature']]['b'][0]
                        else:
                            norm_value = f['value']
                    elif f['type'] == 'ARRAY':
                        if coeffs:
                            norm_value = []
                            for i in range(len(f['value'])):
                                norm_value.append(coeffs[f['feature']]['a'][i] * f['value'][i] + coeffs[f['feature']]['b'][i])
                        else:
                            norm_value = f['value']
                    else:
                        norm_value = f['value']
                    filter += " " + self.prepend_value_label(f) + f['feature'] + "=" + str(norm_value) + " "

                else:
                    filter += " "
                    if f['value']['min']:
                        if coeffs:
                            norm_value = coeffs[f['feature']]['a'][0] * f['value']['min'] + coeffs[f['feature']]['b'][0]
                        else:
                            norm_value = f['value']['min']
                        filter += self.prepend_value_label(f) + f['feature'] + ">" + str(norm_value) + " "
                    if f['value']['max']:
                        if f['value']['min']:
                            filter += "AND "
                        if coeffs:
                            norm_value = coeffs[f['feature']]['a'][0] * f['value']['max'] + coeffs[f['feature']]['b'][0]
                        else:
                            norm_value = f['value']['max']
                        filter += self.prepend_value_label(f) + f['feature'] + "<" + str(norm_value) + " "

        return filter
