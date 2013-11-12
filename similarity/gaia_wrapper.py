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
from similarity_settings import SIMILARITY_MINIMUM_POINTS, INDEX_DIR, DEFAULT_PRESET, PRESETS, PRESET_DIR, INDEX_NAME, BAD_REQUEST_CODE, NOT_FOUND_CODE, SERVER_ERROR_CODE
from similarity_server_utils import generate_structured_dict_from_layout, get_nested_dictionary_value, get_nested_descriptor_names, set_nested_dictionary_value, parse_filter_list
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

            logger.info('Dataset loaded, size: %s points' % (self.original_dataset.size()))

        else:
            # If there is no existing dataset we create an empty one.
            # For the moment we do not create any distance metric nor a view because search won't be possible until the DB has a minimum of SIMILARITY_MINIMUM_POINTS
            self.original_dataset.save(self.original_dataset_path)
            logger.info('Created new dataset, size: %s points (should be 0)' % (self.original_dataset.size()))


    def __prepare_original_dataset(self):
        logger.info('Preparing the original dataset.')
        self.original_dataset = self.prepare_original_dataset_helper(self.original_dataset)

    def __normalize_original_dataset(self):
        logger.info('Normalizing the original dataset.')
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
            logger.info('Bulding metric for preset %s' % preset)
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
            logger.info('Added point with name %s. Index has now %i points.' % (str(point_name),size))
        except:
            msg = 'Point with name %s could NOT be added. Index has now %i points.' % (str(point_name),size)
            logger.info(msg)
            return {'error':True, 'result':msg, 'status_code': SERVER_ERROR_CODE}

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
            logger.info('Deleted point with name %s. Index has now %i points.' % (str(point_name),self.original_dataset.size()))
            return {'error':False, 'result':True}
        else:
            msg = 'Can\'t delete point with name %s because it does not exist.'% str(point_name)
            logger.info(msg)
            return {'error':True,'result':msg, 'status_code': NOT_FOUND_CODE}

    def get_point(self, point_name):
        logger.info('Getting point with name %s' % str(point_name))
        if self.original_dataset.contains(str(point_name)):
            return self.original_dataset.point(str(point_name))


    def save_index(self, filename = None, msg = ""):
        tic = time.time()
        path = self.original_dataset_path
        if filename:
            path =  INDEX_DIR + filename + ".db"
        logger.info('Saving index to (%s)...'%path + msg)
        self.original_dataset.save(path)
        toc = time.time()
        logger.info('Finished saving index (done in %.2f seconds, index has now %i points).'%((toc - tic),self.original_dataset.size()))
        return {'error':False,'result':path}


    def contains(self, point_name):
        logger.info('Checking if index has point with name %s' % str(point_name))
        return {'error':False,'result':self.original_dataset.contains(point_name)}


    def get_sounds_descriptors(self, point_names, descriptor_names=None, normalization=True, only_leaf_descriptors=False):
        '''
        Returns a list with the descritor values for all requested point names
        '''

        logger.info('Getting descriptors for points %s' % ','.join([str(name) for name in point_names]))

        data = dict()
        required_descriptor_names = self.__calculate_complete_required_descriptor_names(descriptor_names, only_leaf_descriptors=only_leaf_descriptors)
        for point_name in point_names:
            sound_descriptors = self.__get_point_descriptors(point_name, required_descriptor_names, normalization)
            if 'error' not in sound_descriptors:
                data[point_name] = sound_descriptors

        return {'error': False, 'result': data}


    def __calculate_complete_required_descriptor_names(self, descriptor_names, only_leaf_descriptors=False):
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
                    if not only_leaf_descriptors:
                        # Return all nested descriptor names
                        extra_names = []
                        get_nested_descriptor_names(nested_descriptors, extra_names)
                        for extra_name in extra_names:
                            processed_descriptor_names.append('%s.%s' % (name, extra_name))
            processed_descriptor_names = list(set(processed_descriptor_names))
            return processed_descriptor_names

        except:
            return {'error': True, 'result': 'Wrong descriptor names, unable to create layout.', 'status_code': BAD_REQUEST_CODE}


    def __get_point_descriptors(self, point_name, required_descriptor_names, normalization=True):
        # Get normalization coefficients to transform the input data (get info from the last
        # transformation which has been a normalization)

        normalization_coeffs = None
        if not normalization:
            trans_hist = self.original_dataset.history().toPython()
            for i in range(0,len(trans_hist)):
                if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                    normalization_coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        required_layout = generate_structured_dict_from_layout(required_descriptor_names)
        try:
            p = self.original_dataset.point(str(point_name))
        except:
            return {'error': True, 'result': 'Sound does not exist in gaia index.', 'status_code': NOT_FOUND_CODE}

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

    def search_dataset(self, query_point, number_of_results, preset_name, offset=0, descriptors_data=None):
        preset_name = str(preset_name)
        results = []
        count = 0
        size = self.original_dataset.size()
        if size < SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS)
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': SERVER_ERROR_CODE}

        if query_point:
            query_point = str(query_point)
            logger.info('NN search for point with name %s (preset = %s)' % (query_point,preset_name))
            results = []

            if query_point.endswith('.yaml'):
                # The point doesn't exist in the dataset....
                # So, make a temporary point, add all the transformations
                # to it and search for it
                p, p1 = Point(), Point()
                p.load(query_point)
                p1 = self.original_dataset.history().mapPoint(p)
                results = self.view.nnSearch(p1, self.metrics[preset_name]).get(int(number_of_results), offset=int(offset))
                count = self.view.nnSearch(p1, self.metrics[preset_name]).size()
            else:
                if not self.original_dataset.contains(query_point):
                    msg = "Sound with id %s doesn't exist in the dataset." % query_point
                    logger.info(msg)
                    return {'error':True,'result':msg, 'status_code': NOT_FOUND_CODE}
                results = self.view.nnSearch(query_point, self.metrics[preset_name]).get(int(number_of_results), offset=int(offset))
                count = self.view.nnSearch(query_point, self.metrics[preset_name]).size()

        if descriptors_data:
            # Create a point with the data in 'descriptors_data' and search for it
            try:
                logger.info('NN search for point of uploaded file')
                p, p1 = Point(), Point()
                p.loadFromString(yaml.dump(descriptors_data))
                p1 = self.original_dataset.history().mapPoint(p)
                results = self.view.nnSearch(p1, self.metrics[preset_name]).get(int(number_of_results), offset=int(offset))
                count = self.view.nnSearch(p1, self.metrics[preset_name]).size()
            except:
                msg = 'Unable to create gaia point from uploaded file.'
                logger.info(msg)
                return {'error': True, 'result': msg}

        return {'error': False, 'result': {'results': results, 'count': count}}


    # CONTENT-BASED SEARCH (API)
    def query_dataset(self, query_parameters, number_of_results, preset_name, offset=0, target_sound_id=False, use_file_as_target=False, descriptors_data=None):

        size = self.original_dataset.size()
        if size < SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS)
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': SERVER_ERROR_CODE}

        trans_hist = self.original_dataset.history().toPython()
        layout = self.original_dataset.layout()

        # Get normalization coefficients to transform the input data (get info from the last transformation which has
        # been a normalization)
        coeffs = None
        for i in range(0,len(trans_hist)):
            if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        ##############
        # PARSE TARGET
        ##############

        if not use_file_as_target:
            # If the target is a sound id (target_sound_id!=False), we get the point of this sound and set as target.
            # Otherwise we create a point and add the descriptors provided
            if target_sound_id:
                query_point = str(target_sound_id)
                if not self.original_dataset.contains(query_point):
                    msg = "Sound with id %s doesn't exist in the dataset and can not be set as descriptors_target." % query_point
                    logger.info(msg)
                    return {'error':True,'result':msg, 'status_code':NOT_FOUND_CODE}
                else:
                    q = query_point

            else:
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
        else:
            # Target is specified as the attached file
            # Create a point with the data in 'descriptors_data' and search for it
            try:
                p, q = Point(), Point()
                p.loadFromString(yaml.dump(descriptors_data))
                q = self.original_dataset.history().mapPoint(p)
            except:
                msg = 'Unable to create gaia point from uploaded file. Probably the file does not have the required layout.'
                logger.info(msg)
                return {'error': True, 'result': msg, 'status_code':SERVER_ERROR_CODE}

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
        if not use_file_as_target:
            if target_sound_id:
                logger.info("Content based search with target: " + str(target_sound_id) + " (sound id) and filter: " + str(filter) )
            else:
                logger.info("Content based search with target: " + str(query_parameters['target']) + " and filter: " + str(filter) )
        else:
            logger.info("Content based search with give analysis file as target.")

        # If target is a sound id or a file, we use the metric of the preset specified in preset parameter. Otherwise we create a
        # metric with the calculated feature_names
        if target_sound_id or use_file_as_target:
            metric = self.metrics[preset_name]
        else:
            metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': feature_names})

        results = self.view.nnSearch(q, metric, str(filter)).get(int(number_of_results), offset=int(offset))
        count = self.view.nnSearch(q, metric, str(filter)).size()

        return {'error': False, 'result': {'results': results, 'count': count}}


    def search(self, target_type, target, filter, preset_name, metric_descriptor_names, num_results, offset):

        # Check if index has sufficient points
        size = self.original_dataset.size()
        if size < SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS)
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': SERVER_ERROR_CODE}

        # Get some dataset parameters that will be useful later
        trans_hist = self.original_dataset.history().toPython()
        layout = self.original_dataset.layout()
        coeffs = None  # Get normalization coefficients
        for i in range(0,len(trans_hist)):
            if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']
                
        # Set query metric
        metric = self.metrics[preset_name]
        if metric_descriptor_names:
            metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': metric_descriptor_names})

        # Process target
        if target:
            if target_type == 'sound_id':
                query_point = str(target)
                if not self.original_dataset.contains(query_point):
                    msg = "Sound with id %s doesn't exist in the dataset and can not be set as similarity target." % query_point
                    logger.info(msg)
                    return {'error': True, 'result': msg, 'status_code': NOT_FOUND_CODE}
                else:
                    query = query_point

            elif target_type == 'descriptor_values':
                # Transform input params to the normalized feature space and add them to a query point
                # If there are no params specified in the target, the point is set as empty (probably random sounds are returned)
                feature_names = []
                query = Point()
                query.setLayout(layout)
                try:
                    for param in target.keys():
                        # Only add numerical parameters. Non numerical ones (like key) are only used as filters
                        if param in coeffs.keys():
                            feature_names.append(str(param))
                            value = target[param]
                            if coeffs:
                                a = coeffs[param]['a']
                                b = coeffs[param]['b']
                                if len(a) == 1:
                                    norm_value = a[0]*value + b[0]
                                else:
                                    norm_value = []
                                    for i in range(0,len(a)):
                                        norm_value.append(a[i]*value[i]+b[i])
                                query.setValue(str(param), norm_value)
                            else:
                                query.setValue(str(param), value)
                except:
                    return {'error': True, 'result': 'Invalid target (descriptor values could not be correctly parsed)', 'status_code': BAD_REQUEST_CODE}

                # Overwrite metric with present descriptors in target
                metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': feature_names})

            elif target_type == 'file':
                # Target is specified as the attached file
                # Create a point with the data in 'descriptors_data' and search for it
                try:
                    p, query = Point(), Point()
                    p.loadFromString(yaml.dump(target))
                    query = self.original_dataset.history().mapPoint(p)
                except:
                    msg = 'Unable to create gaia point from uploaded file. Probably the file does not have the required layout.'
                    logger.info(msg)
                    return {'error': True, 'result': msg, 'status_code': SERVER_ERROR_CODE}
        else:
            query = Point()  # Empty target
            query.setLayout(layout)

        # Process filter
        if filter:
            filter = parse_filter_list(filter, coeffs)
        else:
            filter = ""  # Empty filter

        # log
        log_message = 'Similarity search'
        if target:
            if target_type == 'sound_id':
                log_target = '%s (sound id)' % str(target)
            elif target_type == 'descriptor_values':
                log_target = '%s (descriptor values)' % str(target)
            elif target_type == 'file':
                log_target = 'uploaded file'
            log_message += ' with target: %s' % log_target
        if filter:
            log_message += ' with filter: %s' % str(filter)
        logger.info(log_message)

        # Do query!
        try:
            search = self.view.nnSearch(query, metric, str(filter))
            results = search.get(num_results, offset=offset)
            count = search.size()
        except:
            return {'error': True, 'result': 'Server error', 'status_code': SERVER_ERROR_CODE}

        return {'error': False, 'result': {'results': results, 'count': count}}


    # UTILS for content-based search
    def get_layout_descriptor_names(self):
        return self.original_dataset.layout().descriptorNames()
