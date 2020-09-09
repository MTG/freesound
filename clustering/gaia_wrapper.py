import logging
import os
import json

from django.conf import settings
from gaia2 import DataSet, View, DistanceFunctionFactory
import numpy as np

import clustering_settings as clust_settings


logger = logging.getLogger('clustering')


class GaiaWrapperClustering:
    """Gaia wrapper for the clustering engine.

    This class contains helper methods to interface with Gaia.
    When creating the instance object, Gaia datasets corresponding to the features configured in the clustering 
    settings file will be loaded.
    """
    def __init__(self):
        self.index_path = clust_settings.INDEX_DIR
        self.__load_datasets()

    def __get_dataset_path(self, ds_name):
        return os.path.join(clust_settings.INDEX_DIR, ds_name + '.db')

    def __load_dataset(self, features, gaia_index, gaia_descriptor_names, gaia_metric):
        """Loads a Gaia dataset, view and metric for a specific feature and config.
        
        Args: 
            features (str): name of the features to be used for clustering. 
                Available features are listed in the clustering settings file
            gaia_index (str): Name of the Gaia dataset index file.
            gaia_descriptor_names (str or List[str]): Name(s) of the descriptor field to use within the Gaia dataset. 
            gaia_metric (str): Name of the metric to use for nearest neighbors search.
        """
        gaia_dataset = DataSet()
        gaia_dataset.load(self.__get_dataset_path(gaia_index))
        gaia_view = View(gaia_dataset)
        gaia_metric = DistanceFunctionFactory.create(gaia_metric, gaia_dataset.layout(), 
            {'descriptorNames': gaia_descriptor_names})

        setattr(self, '{}_dataset'.format(features), gaia_dataset)
        setattr(self, '{}_view'.format(features), gaia_view)
        setattr(self, '{}_metric'.format(features), gaia_metric)

        # ds_name = 'FS_AS_embeddings_mean_max_min_nrg_normalized'
        # self.features = np.load(os.path.join(clust_settings.INDEX_DIR, ds_name + '.npy'))
        # self.id2idx = json.load(open(os.path.join(clust_settings.INDEX_DIR, ds_name + '_idx.json')))

    def __load_datasets(self):
        """Loads all the Gaia datasets corresponding to the features that are configured in the clustering settings.
        """
        logger.info('Loading datasets for each features used in clustering')
        for feature_string, feature_config in clust_settings.AVAILABLE_FEATURES.items():
            if feature_config:
                self.__load_dataset(feature_string, feature_config['DATASET_FILE'], 
                                    feature_config['GAIA_DESCRIPTOR_NAMES'], feature_config['GAIA_METRIC'])
                logger.info('{} dataset loaded'.format(feature_string))

    def search_nearest_neighbors(self, sound_id, k, in_sound_ids=[], features=clust_settings.DEFAULT_FEATURES):
        """Find the k nearest neighbours of a target sound within a given subset of sounds and set of features

        Args:
            sound_id (str): id of the sound query.
            k (int): number of nearest neighbors to retrieve.
            in_sound_ids (List[str]): ids of the subset of sounds within the one we perform the Nearest Neighbors search.
            features (str): name of the features to be used for nearest neighbors computation. 
                Available features are listed in the clustering settings file

        Returns:
            List[str]: ids of the retrieved sounds.
        """
        if in_sound_ids:
            filter = 'WHERE point.id IN ("' + '", "'.join(in_sound_ids) + '")'
        else:
            filter = None
        try:
            gaia_view = getattr(self, '{}_view'.format(features))
            gaia_metric = getattr(self, '{}_metric'.format(features))
            nearest_neighbors = gaia_view.nnSearch(sound_id, gaia_metric, filter).get(k)[1:]

            if not nearest_neighbors:
                logger.info("No nearest neighbors found for point with id '{}'".format(sound_id))

            return nearest_neighbors

        except AttributeError:
            logger.info('The requested gaia view or metric corresponding to "{}" features does not exist'.format(features))

        except Exception as e:
            logger.info(e)
            return []

    def return_sound_reference_features(self, sound_ids):
        """Returns the reference features for the given sounds that are used for evaluating the clustering performance.

        The reference features defined in the clustering settings file.
        They typically consists of features derived from the sounds' tags.

        Args:
            sound_ids (List[str]): list containing the ids of the sounds we want the features.

        Returns:
            List[List[Float]]: list containing the reference features of the requested sounds.
        """
        reference_features = []
        gaia_dataset = getattr(self, '{}_dataset'.format(clust_settings.REFERENCE_FEATURES))
        gaia_descriptor_names = clust_settings.AVAILABLE_FEATURES[clust_settings.REFERENCE_FEATURES]['GAIA_DESCRIPTOR_NAMES']
        for sound_id in sound_ids:
            try:
                reference_features.append(gaia_dataset.point(sound_id).value(gaia_descriptor_names))
            except Exception as e:
                # Gaia raises only broad exceptions. Here it would correspond to a sound that is not found in the dataset
                logger.info(e)
                reference_features.append(None)
        return reference_features

    def return_features(self, sound_ids):
        # existing_id = set(self.id2idx.keys())
        # sound_ids_out = [sound_id for sound_id in sound_ids if sound_id in existing_id]
        # indexes = [self.id2idx[sound_id] for sound_id in sound_ids_out]
        # features = self.features[indexes]

        # return features, sound_ids_out

        features = []
        sound_ids_out = []
        gaia_dataset = getattr(self, '{}_dataset'.format(clust_settings.DEFAULT_FEATURES))
        gaia_descriptor_names = clust_settings.AVAILABLE_FEATURES[clust_settings.DEFAULT_FEATURES]['GAIA_DESCRIPTOR_NAMES']
        for sound_id in sound_ids:
            try:
                features.append(list(gaia_dataset.point(sound_id).value(gaia_descriptor_names)))
                sound_ids_out.append(sound_id)
            except Exception as e:
                # Gaia raises only broad exceptions. Here it would correspond to a sound that is not found in the dataset
                logger.info(e)
        return np.array(features).astype('float32'), sound_ids_out
