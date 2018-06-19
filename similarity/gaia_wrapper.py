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

import logging
import os
import time

import yaml
from gaia2 import DataSet, transform, DistanceFunctionFactory, View, Point, VariableLength

from similarity_server_utils import generate_structured_dict_from_layout, get_nested_dictionary_value, \
    get_nested_descriptor_names, set_nested_dictionary_value, parse_filter_list
import similarity_settings as sim_settings

logger = logging.getLogger('similarity')


class GaiaWrapper:

    def __init__(self, indexing_only_mode=False):
        self.indexing_only_mode = indexing_only_mode
        self.index_path = sim_settings.INDEX_DIR
        self.original_dataset = DataSet()
        self.pca_dataset = DataSet()
        if not self.indexing_only_mode:
            self.original_dataset_path = self.__get_dataset_path(sim_settings.INDEX_NAME)
        else:
            self.original_dataset_path = self.__get_dataset_path(sim_settings.INDEXING_SERVER_INDEX_NAME)
        self.descriptor_names = {}
        self.metrics = {}
        self.view = None
        self.view_pca = None
        self.transformations_history = None

        self.__load_dataset()

    def __get_dataset_path(self, ds_name):
        return os.path.join(sim_settings.INDEX_DIR, ds_name + '.db')

    def __load_dataset(self):
        """
        Loads the dataset, does all the necessary steps to make it available for similarity queries and creates the PCA
        version of it. If dataset does not exist, creates a new empty one.
        NOTE: we assume that loaded datasets will have been prepared and normalized (see_
        _prepare_original_dataset() and __normalize_original_dataset()) on due time (see add_point() method below),
        therefore this function does not prepare or normalize loaded datasets.
        """

        if not os.path.exists(sim_settings.INDEX_DIR):
            os.makedirs(sim_settings.INDEX_DIR)

        # load original dataset
        if os.path.exists(self.original_dataset_path):
            self.original_dataset.load(self.original_dataset_path)
            self.__calculate_descriptor_names()

            if self.original_dataset.size() >= sim_settings.SIMILARITY_MINIMUM_POINTS and not self.indexing_only_mode:

                # Save transformation history so we do not need to compute it every time we need it
                self.transformations_history = self.original_dataset.history().toPython()

                # Build metrics for the different similarity presets, create a Gaia view
                self.__build_metrics()
                view = View(self.original_dataset)
                self.view = view

                # Compute PCA and create pca view and metric
                # NOTE: this step may take a long time if the dataset is big, but it only needs to be performed once
                # when the similarity server is loaded-
                self.pca_dataset = transform(self.original_dataset, 'pca',
                                             {'descriptorNames': sim_settings.PCA_DESCRIPTORS,
                                              'dimension': sim_settings.PCA_DIMENSIONS,
                                              'resultName': 'pca'})
                self.pca_dataset.setReferenceDataSet(self.original_dataset)
                self.view_pca = View(self.pca_dataset)
                self.__build_pca_metric()

            if self.original_dataset.history().size() <= 0:
                logger.info('Dataset loaded, size: %s points' % (self.original_dataset.size()))
            else:
                logger.info('Dataset loaded, size: %s points (%i fixed-length desc., %i variable-length desc.)' %
                            (self.original_dataset.size(),
                             len(self.descriptor_names['fixed-length']),
                             len(self.descriptor_names['variable-length'])))

        else:
            # If there is no existing dataset we create an empty one.
            # For the moment we do not create any distance metric nor a view because search won't be possible until
            # the DB has a minimum of SIMILARITY_MINIMUM_POINTS
            self.original_dataset.save(self.original_dataset_path)
            self.__calculate_descriptor_names()
            logger.info('Created new dataset, size: %s points (should be 0)' % (self.original_dataset.size()))

    def __prepare_original_dataset(self):
        logger.info('Preparing the original dataset.')
        self.original_dataset = self.prepare_original_dataset_helper(self.original_dataset)
        self.__calculate_descriptor_names()

    def __normalize_original_dataset(self):
        logger.info('Normalizing the original dataset.')
        self.original_dataset = self.normalize_dataset_helper(self.original_dataset,
                                                              self.descriptor_names['fixed-length'])

    def __calculate_descriptor_names(self):
        layout = self.original_dataset.layout()
        all_descriptor_names = layout.descriptorNames()
        fixed_length_descritpor_names = []
        variable_length_descritpor_names = []
        multidimensional_descriptor_names = []

        for name in all_descriptor_names:
            region = layout.descriptorLocation(name)
            if region.lengthType() == VariableLength:
                variable_length_descritpor_names.append(name)
            else:
                fixed_length_descritpor_names.append(name)
                try:
                    if region.dimension() > 1:
                        multidimensional_descriptor_names.append(name)
                except:  # TODO: exception too broad here...
                    pass

        self.descriptor_names = {'all': all_descriptor_names,
                                 'fixed-length': fixed_length_descritpor_names,
                                 'variable-length': variable_length_descritpor_names,
                                 'multidimensional': multidimensional_descriptor_names}

    @staticmethod
    def prepare_original_dataset_helper(ds):
        ds = transform(ds, 'FixLength')  # Needed to optimize use of fixed-length descriptors and save memory
        ds = transform(ds, 'Cleaner')  # Remove descriptors that will cause problems in further transformations
        try:
            ds = transform(ds, 'enumerate', {'descriptorNames': ['.tonal.chords_progression']})
        except:  # TODO: exception too broad here...
            logger.info('WARNING: enumerate transformation to .tonal.chords_progression could not be performed.')
        return ds

    @staticmethod
    def normalize_dataset_helper(ds, descriptor_names):
        # NOTE: The "except" list of descriptors below should be reviewed if a new extractor is used. The point is to
        # remove descriptors can potentially break normalize transform (e.g. descriptors with value = 0)
        normalization_params = {"descriptorNames": descriptor_names,
                                "except": [
                                    "*.min",
                                    "*.max",
                                    "tonal.chords_histogram",
                                ],
                                "independent": True, "outliers": -1}
        ds = transform(ds, 'normalize', normalization_params)
        return ds

    def __build_metrics(self):
        for preset in sim_settings.PRESETS:
            if preset != 'pca':  # PCA metric is built only after pca dataset is created so it should not be built here
                logger.info('Bulding metric for preset %s' % preset)
                name = preset
                path = sim_settings.PRESET_DIR + name + ".yaml"
                preset_file = yaml.load(open(path))
                distance = preset_file['distance']['type']
                parameters = preset_file['distance']['parameters']
                search_metric = DistanceFunctionFactory.create(
                    str(distance), self.original_dataset.layout(), parameters)
                self.metrics[name] = search_metric

    def __build_pca_metric(self):
        logger.info('Bulding metric for preset pca')
        preset_file = yaml.load(open(sim_settings.PRESET_DIR + "pca.yaml"))
        distance = preset_file['distance']['type']
        parameters = preset_file['distance']['parameters']
        search_metric = DistanceFunctionFactory.create(str(distance), self.pca_dataset.layout(), parameters)
        self.metrics['pca'] = search_metric

    def add_point(self, point_location, point_name):

        if self.original_dataset.contains(str(point_name)):
                self.original_dataset.removePoint(str(point_name))

        p = Point()
        if os.path.exists(str(point_location)):
            try:
                p.load(str(point_location))
                p.setName(str(point_name))
                if self.original_dataset.size() <= sim_settings.SIMILARITY_MINIMUM_POINTS:
                    # Add point to original_dataset because PCA dataset has not been created yet
                    self.original_dataset.addPoint(p)
                    msg = 'Added point with name %s. Index has now %i points.' % \
                          (str(point_name), self.original_dataset.size())
                    logger.info(msg)
                else:
                    # Add point to PCA dataset because it has been already created.
                    # PCA dataset will take care of adding the point to the original dataset as well.
                    self.pca_dataset.addPoint(p)
                    msg = 'Added point with name %s. Index has now %i points (pca index has %i points).' % \
                          (str(point_name), self.original_dataset.size(), self.pca_dataset.size())
                    logger.info(msg)

            except Exception as e:
                msg = 'Point with name %s could NOT be added (%s).' % (str(point_name), str(e))
                logger.info(msg)
                return {'error': True, 'result': msg, 'status_code': sim_settings.SERVER_ERROR_CODE}
        else:
            msg = 'Point with name %s could NOT be added because analysis file does not exist (%s).' % \
                  (str(point_name), str(point_location))
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': sim_settings.SERVER_ERROR_CODE}

        if self.original_dataset.size() == sim_settings.SIMILARITY_MINIMUM_POINTS:
            # Do enumerate
            try:
                self.original_dataset = transform(self.original_dataset, 'enumerate',
                                                  {'descriptorNames': ['.tonal.chords_progression']})
            except:  # TODO: exception too broad here...
                logger.info('WARNING: enumerate transformation to .tonal.chords_progression could not be performed.')

        # If when adding a new point we reach the minimum points for similarity, do the needful so that the dataset
        # can be used for search. This includes preparing the dataset, normalizing it, saveing it and creating view and
        # distance metrics. This will only happen once when the size of the dataset reaches SIMILARITY_MINIMUM_POINTS.
        if self.original_dataset.size() == sim_settings.SIMILARITY_MINIMUM_POINTS and not self.indexing_only_mode:
            self.__prepare_original_dataset()
            self.__normalize_original_dataset()
            self.transformations_history = self.original_dataset.history().toPython()
            self.save_index(msg="(reaching %i points)" % sim_settings.SIMILARITY_MINIMUM_POINTS)

            # TODO: the code below is repeated from __load_dataset() method, should be moved into a util function
            # Build metrics for the different similarity presets, create a Gaia view
            self.__build_metrics()
            view = View(self.original_dataset)
            self.view = view

            # Compute PCA and create pca view and metric
            # NOTE: this step may take a long time if the dataset is big, but it only needs to be performed once
            # when the similarity server is loaded-
            self.pca_dataset = transform(self.original_dataset, 'pca',
                                         {'descriptorNames': sim_settings.PCA_DESCRIPTORS,
                                          'dimension': sim_settings.PCA_DIMENSIONS,
                                          'resultName': 'pca'})
            self.pca_dataset.setReferenceDataSet(self.original_dataset)
            self.view_pca = View(self.pca_dataset)
            self.__build_pca_metric()

        return {'error': False, 'result': msg}

    def delete_point(self, point_name):
        if self.original_dataset.contains(str(point_name)):
            if self.original_dataset.size() <= sim_settings.SIMILARITY_MINIMUM_POINTS:
                # Remove from original dataset
                self.original_dataset.removePoint(str(point_name))
            else:
                # Remove from pca dataset (pca dataset will take care of removing from original dataset too)
                self.pca_dataset.removePoint(str(point_name))
            logger.info('Deleted point with name %s. Index has now %i points (pca index has %i points).' %
                        (str(point_name), self.original_dataset.size(), self.pca_dataset.size()))
            return {'error': False, 'result': True}
        else:
            msg = 'Can\'t delete point with name %s because it does not exist.' % str(point_name)
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': sim_settings.NOT_FOUND_CODE}

    def get_point(self, point_name):
        logger.info('Getting point with name %s' % str(point_name))
        if self.original_dataset.contains(str(point_name)):
            return self.original_dataset.point(str(point_name))

    def get_all_point_names(self):
        point_names = sorted([int(name) for name in self.original_dataset.pointNames()])
        logger.info('Getting all point names (%i points)' % len(point_names))
        return {'error': False, 'result': point_names}

    def save_index(self, filename=None, msg=""):
        tic = time.time()
        path = self.original_dataset_path
        if filename:
            path = sim_settings.INDEX_DIR + filename + ".db"
        logger.info('Saving index to (%s)...' % path + msg)
        self.original_dataset.save(path)
        toc = time.time()
        logger.info('Finished saving index (done in %.2f seconds, index has now %i points).' %
                    ((toc - tic), self.original_dataset.size()))
        return {'error': False, 'result': path}

    def contains(self, point_name):
        logger.info('Checking if index has point with name %s' % str(point_name))
        return {'error': False, 'result': self.original_dataset.contains(point_name)}

    def get_sounds_descriptors(self,
                               point_names, descriptor_names=None, normalization=True, only_leaf_descriptors=False):
        """
        Returns a list with the descriptor values for all requested point names
        """

        logger.info('Getting descriptors for points %s' % ','.join([str(name) for name in point_names]))

        # Add dot '.' at the beginning of descriptor names if not present
        if descriptor_names:
            descriptor_names_aux = list()
            for name in descriptor_names:
                if name[0] != '.':
                    descriptor_names_aux.append('.' + name)
                else:
                    descriptor_names_aux.append(name)
            descriptor_names = descriptor_names_aux[:]
        data = dict()
        required_descriptor_names = self.__calculate_complete_required_descriptor_names(
            descriptor_names, only_leaf_descriptors=only_leaf_descriptors)

        if type(required_descriptor_names) == dict:
            return required_descriptor_names  # There has been an error

        for point_name in point_names:
            sound_descriptors = self.__get_point_descriptors(point_name, required_descriptor_names, normalization)
            if 'error' not in sound_descriptors:
                data[point_name] = sound_descriptors

        return {'error': False, 'result': data}

    def __calculate_complete_required_descriptor_names(self, descriptor_names, only_leaf_descriptors=False):
        if not descriptor_names:
            descriptor_names = self.descriptor_names['all'][:]
        try:
            structured_layout = generate_structured_dict_from_layout(self.descriptor_names['all'][:])
            processed_descriptor_names = []
            for name in descriptor_names:
                nested_descriptors = get_nested_dictionary_value(name.split('.')[1:], structured_layout)
                if not nested_descriptors:
                    processed_descriptor_names.append(name)
                else:
                    if only_leaf_descriptors:
                        # only return descriptors if nested descriptors are statistics
                        if len(set(nested_descriptors.keys()).intersection(
                                ['min', 'max', 'dvar2', 'dmean2', 'dmean', 'var', 'dvar', 'mean'])) > 0:
                            for extra_name in nested_descriptors.keys():
                                processed_descriptor_names.append('%s.%s' % (name, extra_name))
                    else:
                        # Return all nested descriptor names
                        extra_names = []
                        get_nested_descriptor_names(nested_descriptors, extra_names)
                        for extra_name in extra_names:
                            processed_descriptor_names.append('%s.%s' % (name, extra_name))
            processed_descriptor_names = list(set(processed_descriptor_names))
            return processed_descriptor_names
        except:
            return {'error': True,
                    'result': 'Wrong descriptor names, unable to create layout.',
                    'status_code': sim_settings.BAD_REQUEST_CODE}

    def __get_point_descriptors(self, point_name, required_descriptor_names, normalization=True):
        """
        Get normalization coefficients to transform the input data (get info from the last transformation which has
        been a normalization)
        """

        normalization_coeffs = None
        if not normalization:
            trans_hist = self.transformations_history
            for i in range(0, len(trans_hist)):
                if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                    normalization_coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        required_layout = generate_structured_dict_from_layout(required_descriptor_names)
        try:
            p = self.original_dataset.point(str(point_name))
        except:
            return {'error': True, 'result': 'Sound does not exist in gaia index.', 'status_code': sim_settings.NOT_FOUND_CODE}

        for descriptor_name in required_descriptor_names:
            try:
                value = p.value(str(descriptor_name))
                if normalization_coeffs:
                    if descriptor_name in normalization_coeffs:
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
                try:
                    value = p.label(str(descriptor_name))
                except:
                    value = None

            if descriptor_name[0] == '.':
                descriptor_name = descriptor_name[1:]
            set_nested_dictionary_value(descriptor_name.split('.'), required_layout, value)
        return required_layout

    # SIMILARITY SEARCH and CONTENT SEARCH

    def search_dataset(self, query_point, number_of_results, preset_name, offset=0):
        preset_name = str(preset_name)
        results = []
        count = 0
        size = self.original_dataset.size()
        if size < sim_settings.SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, sim_settings.SIMILARITY_MINIMUM_POINTS)
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': sim_settings.SERVER_ERROR_CODE}

        query_point = str(query_point)
        logger.info('NN search for point with name %s (preset = %s)' % (query_point,preset_name))
        results = []

        if not self.original_dataset.contains(query_point):
            msg = "Sound with id %s doesn't exist in the dataset." % query_point
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': sim_settings.NOT_FOUND_CODE}
        if preset_name == 'pca':
            # Search on PCA view
            search = self.view_pca.nnSearch(query_point, self.metrics[preset_name])
        else:
            # Search on original dataset view
            search = self.view.nnSearch(query_point, self.metrics[preset_name])
        results = search.get(int(number_of_results), offset=int(offset))
        count = search.size()

        return {'error': False, 'result': {'results': results, 'count': count}}

    def api_search(self, target_type, target, filter, preset_name, metric_descriptor_names, num_results, offset,
                   in_ids):

        # Check if index has sufficient points
        size = self.original_dataset.size()
        if size < sim_settings.SIMILARITY_MINIMUM_POINTS:
            msg = 'Not enough datapoints in the dataset (%s < %s).' % (size, sim_settings.SIMILARITY_MINIMUM_POINTS)
            logger.info(msg)
            return {'error': True, 'result': msg, 'status_code': sim_settings.SERVER_ERROR_CODE}

        # Get some dataset parameters that will be useful later
        trans_hist = self.transformations_history
        layout = self.original_dataset.layout()
        pca_layout = self.pca_dataset.layout()
        coeffs = None  # Get normalization coefficients
        for i in range(0, len(trans_hist)):
            if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        # Process target
        if target:
            if target_type == 'sound_id':
                query_point = str(target)
                if not self.original_dataset.contains(query_point):
                    msg = "Sound with id %s doesn't exist in the dataset and can not be set as similarity target." \
                          % query_point
                    logger.info(msg)
                    return {'error': True, 'result': msg, 'status_code': sim_settings.NOT_FOUND_CODE}
                else:
                    query = query_point

            elif target_type == 'descriptor_values':
                # Transform input params to the normalized feature space and add them to a query point
                # If there are no params specified in the target, the point is set as empty (probably random sounds
                # are returned)
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
                    return {'error': True, 'result': 'Invalid target (descriptor values could not be correctly parsed)',
                            'status_code': sim_settings.BAD_REQUEST_CODE}

                # Overwrite metric with present descriptors in target
                metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': feature_names})

            elif target_type == 'file':
                # Target is specified as the attached file
                # Create a point with the data in 'descriptors_data' and search for it
                target_file_parsing_type = '-'

                try:
                    # Try directly loading the file
                    p, query = Point(), Point()
                    p.loadFromString(yaml.dump(target))
                    if preset_name == 'pca':
                        query = self.pca_dataset.history().mapPoint(p)  # map point to pca dataset
                    else:
                        query = self.original_dataset.history().mapPoint(p)  # map point to original dataset
                    target_file_parsing_type = 'mapPoint'

                except Exception as e:
                    logger.info('Unable to create gaia point from uploaded file (%s). '
                                'Trying adding descriptors one by one.' % e)

                    # If does not work load descriptors one by one
                    try:
                        query = Point()
                        #query.setLayout(layout)

                        feature_names = []
                        get_nested_descriptor_names(target, feature_names)
                        feature_names = ['.%s' % item for item in feature_names]
                        nonused_features = []

                        for param in feature_names:
                            if param in coeffs.keys():
                                value = get_nested_dictionary_value(param[1:].split('.'), target)
                                if coeffs:
                                    try:
                                        a = coeffs[param]['a']
                                        b = coeffs[param]['b']
                                        if len(a) == 1:
                                            norm_value = a[0]*value + b[0]
                                        else:
                                            norm_value = []
                                            for i in range(0,len(a)):
                                                norm_value.append(a[i]*value[i]+b[i])
                                        query.setValue(str(param[1:]), norm_value)
                                    except:
                                        nonused_features.append(param)
                                else:
                                    query.setValue(str(param[1:]), value)
                            else:
                                nonused_features.append(param)

                        if preset_name == 'pca':
                            query = self.pca_dataset.history().mapPoint(query)  # map point to pca dataset
                        else:
                            query = self.original_dataset.history().mapPoint(p)  # map point to original dataset

                        target_file_parsing_type = 'walkDict'

                    except Exception as e:
                        logger.info('Unable to create gaia point from uploaded file and adding descriptors one by '
                                    'one (%s)' % e)
                        return {'error': True, 'result': 'Unable to create gaia point from uploaded file. Probably the '
                                                         'file does not have the required layout. Are you using the '
                                                         'correct version of Essentia\'s Freesound extractor?',
                                'status_code': sim_settings.SERVER_ERROR_CODE}
        else:
            query = Point()  # Empty target
            if preset_name == 'pca':
                query.setLayout(pca_layout)
            else:
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
                log_target = 'uploaded file (%s)' % target_file_parsing_type
            log_message += ' with target: %s' % log_target
        if filter:
            log_message += ' with filter: %s' % str(filter)
        logger.info(log_message)

        # if in_ids is specified, edit the filter accordingly
        if in_ids:
            if not filter:
                filter = 'WHERE point.id IN ("' + '", "'.join(in_ids) + '")'
            else:
                filter += ' AND point.id IN ("' + '", "'.join(in_ids) + '")'

         # Set query metric
        metric = self.metrics[preset_name]
        if metric_descriptor_names:
            metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': metric_descriptor_names})

        # Do query!
        try:
            if target_type == 'descriptor_values' and target:
                search = self.view.nnSearch(query, metric, str(filter))
            else:
                if preset_name == 'pca':
                    search = self.view_pca.nnSearch(query, metric, str(filter))
                else:
                    search = self.view.nnSearch(query, metric, str(filter))
            results = search.get(num_results, offset=offset)
            count = search.size()
        except Exception as e:
            return {'error': True, 'result': 'Similarity server error', 'status_code': sim_settings.SERVER_ERROR_CODE}

        note = None
        if target_type == 'file':
            if target_file_parsing_type == 'walkDict':
                note = 'The layout of the given analysis file differed from what we expected. Similarity results ' \
                       'might not be accurate. Was the file generated with the last version of Essentia\'s ' \
                       'Freesound extractor?'

        return {'error': False, 'result': {'results': results, 'count': count, 'note': note}}
