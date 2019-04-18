import logging
import os
import sys
import time

import yaml
from gaia2 import DataSet, View, DistanceFunctionFactory

import clustering_settings as clust_settings

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from similarity.gaia_wrapper import GaiaWrapper as GaiaWrapperSimilarity

logger = logging.getLogger('clustering')


class GaiaWrapper:
    def __init__(self):
        self.as_dataset = DataSet()
        self.tag_dataset = DataSet()
        self.fs_dataset = DataSet()
        self.ac_dataset = DataSet()
        self.gaia_similiarity = None

        self.index_path = clust_settings.INDEX_DIR

        self.as_view = None
        self.as_metric = None
        self.tag_view = None
        self.tag_metric = None
        self.fs_view = None
        self.fs_metric = None
        self.ac_view = None
        self.ac_metric = None

        self.__load_datasets()

    def __get_dataset_path(self, ds_name):
        return os.path.join(clust_settings.INDEX_DIR, ds_name + '.db')

    def __load_datasets(self):
        self.as_dataset.load(self.__get_dataset_path(clust_settings.INDEX_NAME_AS))
        self.as_view = View(self.as_dataset)
        # self.metric = DistanceFunctionFactory.create('euclidean', self.dataset.layout())
        # self.metric = DistanceFunctionFactory.create('CosineSimilarity',  self.dataset.layout())
        # self.metric = DistanceFunctionFactory.create('CosineAngle',  self.dataset.layout())
        self.as_metric = DistanceFunctionFactory.create('Manhattan',  self.as_dataset.layout())

        self.tag_dataset.load(self.__get_dataset_path(clust_settings.INDEX_NAME_TAG))
        self.tag_view = View(self.tag_dataset)
        self.tag_metric = DistanceFunctionFactory.create('euclidean', self.tag_dataset.layout())

        self.fs_dataset.load(self.__get_dataset_path(clust_settings.INDEX_NAME_FS))
        self.fs_view = View(self.fs_dataset)
        self.fs_metric = DistanceFunctionFactory.create('euclidean', self.fs_dataset.layout(), {'descriptorNames': 'pca'})

        # self.gaia_similiarity = GaiaWrapperSimilarity()

        self.__load_sc_descriptors_dataset()

    def __load_sc_descriptors_dataset(self):
        self.ac_dataset.load(self.__get_dataset_path('FS_AC_descriptors_normalized'))
        self.ac_view = View(self.ac_dataset)
        self.ac_metric = DistanceFunctionFactory.create('euclidean', self.ac_dataset.layout(), 
            {'descriptorNames': ['ac_brightness', 'ac_boominess', 'ac_depth', 'ac_hardness', 'ac_roughness', 'ac_sharpness', 'ac_warmth']})

    def search_nearest_neighbors(self, sound_id, k, in_sound_ids=[], features='audio_as'):
        if in_sound_ids:
            filter = 'WHERE point.id IN ("' + '", "'.join(in_sound_ids) + '")'
        else:
            filter = None
        try:
            if features == 'audio_as':
                nearest_neighbors = self.as_view.nnSearch(sound_id, self.as_metric, filter).get(k)[1:]
            elif features == 'tag':
                nearest_neighbors = self.tag_view.nnSearch(sound_id, self.tag_metric, filter).get(k)[1:]
            elif features == 'audio_fs':
                nearest_neighbors = self.gaia_similiarity.view_pca.nnSearch(sound_id, 
                                                                            self.gaia_similiarity.metrics['pca'], 
                                                                            filter).get(k)[1:]
            elif features == 'audio_fs_selected':
                nearest_neighbors = self.fs_view.nnSearch(sound_id, self.fs_metric, filter).get(k)[1:]
            elif features == 'audio_ac':
                nearest_neighbors = self.ac_view.nnSearch(sound_id, self.ac_metric, filter).get(k)[1:]

            if not nearest_neighbors:
                logger.info("No nearest neighbors found for point with id '{}'".format(sound_id))
            return nearest_neighbors
        except Exception as e:
            logger.info(e)
            return []

    def return_sound_tag_features(self, sound_ids):
        tag_features = []
        for sound_id in sound_ids:
            try:
                tag_features.append(self.tag_dataset.point(sound_id).value('tags_lda'))  # TODO: add this in clustering settings
            except Exception as e:
                #logger.info(e)
                tag_features.append(None)
        return tag_features
