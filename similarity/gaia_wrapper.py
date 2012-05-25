import os, yaml, shutil, logging
from gaia2 import DataSet, transform, DistanceFunctionFactory, View, Point
from settings import SIMILARITY_MINIMUM_POINTS, INDEX_DIR, PRESET_DIR, PRESETS, SAVE_ON_CHANGE

logger = logging.getLogger('similarity')

class GaiaWrapper:
    '''
    N.B.: if at SIMILARITY_MINIMUM_POINTS you get an error like the following
        "PCA: Specified target dimension (30) is greater than given dataset dimension (0)",
        that probably means all the points are analyses of the same file, and therefore all
        the dimensions were filtered out.
    '''
    def __init__(self):
        self.preset_names               = PRESETS
        self.index_path                 = INDEX_DIR
        self.preset_path                = PRESET_DIR
        self.original_dataset           = DataSet()
        self.original_dataset_path      = self.__get_dataset_path('orig')
        self.preset_datasets            = {}
        self.preset_dataset_paths       = {}
        self.views                      = {}
        self.presets                    = self.__load_preset_files()
        self.__load_datasets()


    def __get_dataset_path(self, ds_name):
        return os.path.join(INDEX_DIR, ds_name + '.db')


    def __load_datasets(self):
        if not os.path.exists(INDEX_DIR):
            os.makedirs(INDEX_DIR)
        # load original dataset
        if os.path.exists(self.original_dataset_path):
            self.original_dataset.load(self.original_dataset_path)
            # if we're loading unprepared datasets, that are the right size, prepare the dataset
            if self.original_dataset.size() >= SIMILARITY_MINIMUM_POINTS \
               and self.original_dataset.history().size() <= 0:
                self.__prepare_original_dataset()
                self.original_dataset.save(self.original_dataset_path)
        else:
            self.original_dataset.save(self.original_dataset_path)
        # load preset datasets
        for preset_name in self.presets.keys():
            ds_path = self.__get_dataset_path(preset_name)
            if os.path.exists(ds_path):
                try:
                    ds = DataSet()
                    ds.load(ds_path)
                    ds.setReferenceDataSet(self.original_dataset)
                    self.__build_view(ds, preset_name)
                    self.preset_datasets[preset_name] = ds
                    self.preset_dataset_paths[preset_name] = ds_path
                except:
                    logger.error('Failed to load preset %s, should we reconstruct it?' % preset_name)
                    #self.__build_preset_dataset_and_save(preset_name)
            else:
                # only create new datasets when the threshold has been reached
                # and we weren't able to load the datasets
                if self.original_dataset.size() >= SIMILARITY_MINIMUM_POINTS:
                    self.__build_preset_dataset_and_save(preset_name)
        logger.debug('Datasets loaded, presets: %s, size: %s' % \
                     (self.preset_datasets.keys(), self.original_dataset.size()))


    def __build_preset_dataset_and_save(self, preset_name):
        logger.debug('Building the preset dataset and saving.')
        ds_path = self.__get_dataset_path(preset_name)
        self.preset_dataset_paths[preset_name] = ds_path
        ds = self.__build_preset_dataset(preset_name)
        self.preset_datasets[preset_name] = ds
        ds.save(ds_path)
        self.__build_view(ds, preset_name)


    def __prepare_original_dataset(self):
        logger.debug('Transforming the original dataset.')
        self.original_dataset = self.prepare_original_dataset_helper(self.original_dataset)

    @staticmethod
    def prepare_original_dataset_helper(ds):
        """This function is used by the inject script as well."""
        proc_ds1  = transform(ds, 'RemoveVL')
        proc_ds2  = transform(proc_ds1,  'FixLength')
        proc_ds1 = None
        prepared_ds = transform(proc_ds2, 'Cleaner')
        return prepared_ds


    def add_point(self, point_location, point_name):
        if self.original_dataset.contains(str(point_name)):
            self.delete_point(str(point_name))
        p = Point()
        p.load(str(point_location))
        p.setName(str(point_name))
        self.original_dataset.addPoint(p)
        size = self.original_dataset.size()
        if size == SIMILARITY_MINIMUM_POINTS:
            self.__prepare_original_dataset()
            for preset_name in self.presets.keys():
                self.__build_preset_dataset_and_save(preset_name)
        else:
            if SAVE_ON_CHANGE:
                for preset_name, preset_ds in self.preset_datasets.items():
                    preset_ds.save(self.preset_dataset_paths[preset_name])
        if SAVE_ON_CHANGE:
            self.original_dataset.save(self.original_dataset_path)

    def contains(self, point_name):
        return self.original_dataset.contains(point_name)

    def search_dataset(self, query_point, number_of_results, preset_name):
        preset_name = str(preset_name)
        query_point = str(query_point)
        size = self.original_dataset.size()
        if (size < SIMILARITY_MINIMUM_POINTS):
            raise Exception('Not enough datapoints in the dataset (%s < %s).' % (size, SIMILARITY_MINIMUM_POINTS))
        if not preset_name in self.presets:
            raise Exception('Invalid preset %s' % preset_name)
        if query_point.endswith('.yaml'):
            #The point doesn't exist in the dataset....
            # So, make a temporary point, add all the transformations
            # to it and search for it
            p, p1 = Point(), Point()
            p.load(query_point)
            p1 = self.preset_datasets[preset_name].history().mapPoint(p)
            similar_songs = self.views[preset_name].nnSearch(p1).get(int(number_of_results))
        else:
            if not self.original_dataset.contains(query_point):
                raise Exception("Sound with id %s doesn't exist in the dataset." % query_point)
            similar_songs = self.views[preset_name].nnSearch(query_point).get(int(number_of_results))
        return similar_songs

    def query_dataset(self, query_parameters, number_of_results):

        preset_name = 'lowlevel'
        view = self.views[preset_name]
        trans_hist = self.preset_datasets[preset_name].history().toPython()
        layout = self.preset_datasets[preset_name].layout()

        # Get normalization coefficients to transform the input data (get info from the last transformation which has been a normalization)
        coeffs = None
        for i in range(0,len(trans_hist)):
            if trans_hist[-(i+1)]['Analyzer name'] == 'normalize':
                coeffs = trans_hist[-(i+1)]['Applier parameters']['coeffs']

        # Transform input params to the normalized feature space and add them to a query point
        q = Point()
        q.setLayout(layout)
        feature_names = []
        for param in query_parameters['target'].keys():
            feature_names.append(param)
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

                text = str(type(param)) + " " + str(type(norm_value))
                logger.debug('ERROR: ' + text)
                q.setValue(param, norm_value)
            else:
                q.setValue(param, value)

        # Parse filter info and costruct filter syntax
        filter = ""
        for param in query_parameters['filter'].keys():
            pass

        metric = DistanceFunctionFactory.create('euclidean', layout, {'descriptorNames': feature_names})
        results = view.nnSearch(q,filter,metric).get(int(number_of_results))
        #results = [[1,0.1],[2,0.2],[3,0.3],[4,0.4]]

        return results


    def delete_point(self, pointname):
        pointname = str(pointname)
        if self.original_dataset.contains(pointname):
            self.original_dataset.removePoint(pointname)
        if SAVE_ON_CHANGE:
            for preset_name, preset_ds in self.preset_datasets.items():
                preset_ds.save(self.preset_dataset_paths[preset_name])
            self.original_dataset.save(self.original_dataset_path)


    def __load_preset_files(self):
        presets = {}
        for preset_name in self.preset_names:
            preset_path = os.path.join(self.preset_path, preset_name + ".yaml")
            if not os.path.exists(preset_path):
                raise Exception('This preset file does not exist (%s).' % preset_path)
            f = file(preset_path, 'r')
            cf = yaml.load(f)
            f.close()
            presets[preset_name] = cf
        return presets


    def __build_preset_dataset(self, preset_name):
        logger.debug('Building preset dataset %s.' % preset_name)
        preset = self.presets[preset_name]
        filter = preset['filter']
        filter_ds = transform(self.original_dataset, filter['type'], filter['parameters'])
        if 'transform' in preset:
            preset_ds = transform(filter_ds,
                                  preset['transform']['type'],
                                  preset['transform']['parameters'])
        else:
            preset_ds = filter_ds
        preset_ds.setReferenceDataSet(self.original_dataset)
        return preset_ds


    def __build_view(self, preset_ds, preset_name):
        logger.debug('Bulding view for preset %s' % preset_name)
        preset = self.presets[preset_name]
        distance = preset['distance']
        search_metric = DistanceFunctionFactory.create(distance['type'],
                                                      preset_ds.layout(),
                                                      distance['parameters'])
        view = View(preset_ds, search_metric)
        preset_ds.addView(view)
        self.views[preset_name] = view
