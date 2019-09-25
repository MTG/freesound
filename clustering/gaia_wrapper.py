import logging
import os
import sys
import time
import yaml
from django.conf import settings

from gaia2 import DataSet, View, DistanceFunctionFactory

import clustering_settings as clust_settings

# for re-using gaia similarity dataset
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from similarity.gaia_wrapper import GaiaWrapper as GaiaWrapperSimilarity

logger = logging.getLogger('clustering')


class GaiaWrapperClustering:
    """Gaia wrapper for the clustering engine.

    This class contains helper methods to interface with Gaia.    
    """
    def __init__(self):
        self.index_path = clust_settings.INDEX_DIR
        self.__load_datasets()

    def __get_dataset_path(self, ds_name):
        return os.path.join(clust_settings.INDEX_DIR, ds_name + '.db')

    def __load_dataset(self, feature_string, gaia_index, gaia_descriptor_names, gaia_metric):
        """Loads a Gaia dataset, view and metric for a specific feature and config.
        
        Args: 
            feature_string (str): String refering the to the features used for clustering.
            gaia_index (str): Name of the Gaia dataset index file.
            gaia_descriptor_names (str or List[str]): Name(s) of the descriptor field to use within the Gaia dataset. 
            gaia_metric (str): Name of the metric to use for nearest neighbors search.
        """
        gaia_dataset = DataSet()
        gaia_dataset.load(self.__get_dataset_path(gaia_index))
        gaia_view = View(gaia_dataset)
        gaia_metric = DistanceFunctionFactory.create(gaia_metric, gaia_dataset.layout(), 
            {'descriptorNames': gaia_descriptor_names})

        setattr(self, '{}_dataset'.format(feature_string), gaia_dataset)
        setattr(self, '{}_view'.format(feature_string), gaia_view)
        setattr(self, '{}_metric'.format(feature_string), gaia_metric)

    def __load_datasets(self):
        """Loads all the Gaia dataset that are configured in the clustering settings.
        """
        logger.info('Loading datasets for each features used in clustering')
        for feature_string, feature_config in clust_settings.AVAILABLE_FEATURES.items():
            if feature_config:
                self.__load_dataset(feature_string, feature_config['DATASET_FILE'], 
                                    feature_config['GAIA_DESCRIPTOR_NAMES'], feature_config['GAIA_METRIC'])
                logger.info('{} dataset loaded'.format(feature_string))

    # TODO: create gaia ds for the fs similarity case
    #     if clust_settings.get('FS_SIMILARITY', False):
    #         self.gaia_similiarity = GaiaWrapperSimilarity()

    def search_nearest_neighbors(self, sound_id, k, in_sound_ids=[], features=clust_settings.DEFAULT_FEATURES):
        """Performs Nearest Neighbors (NN) search on the sound given as query within the given subset with the requested features.

        Args:
            sound_id (str): id of the sound query.
            k (int): number of nearest neighbors to retrieve.
            in_sound_ids (List[str]): ids of the subset of sounds within the one we perform the NN search.
            features (str): name of the features used for nearest neighbors computation (e.g. 'audio_as').

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

            # TODO: create gaia ds for the fs similarity case
            # elif features == 'audio_fs':
            #     nearest_neighbors = self.gaia_similiarity.view_pca.nnSearch(sound_id, 
            #                                                                 self.gaia_similiarity.metrics['pca'], 
            #                                                                 filter).get(k)[1:]

            if not nearest_neighbors:
                logger.info("No nearest neighbors found for point with id '{}'".format(sound_id))
            return nearest_neighbors

        # probably be more specific here...
        except Exception as e:
            logger.info(e)
            return []

    def return_sound_tag_features(self, sound_ids):
        """Returns the tag-based features for the given sounds.

        Args:
            sound_ids (List[str]): list containing the ids of the sounds we want the features.

        Returns:
            List[List[Float]]: list containing the tag-based features of the requested sounds.
        """
        tag_features = []
        gaia_dataset = getattr(self, '{}_dataset'.format(clust_settings.TAG_FEATURES))
        gaia_descriptor_names = clust_settings.AVAILABLE_FEATURES[clust_settings.TAG_FEATURES]['GAIA_DESCRIPTOR_NAMES']
        for sound_id in sound_ids:
            try:
                tag_features.append(gaia_dataset.point(sound_id).value(gaia_descriptor_names))
            except Exception as e:
                #logger.info(e)
                tag_features.append(None)
        return tag_features
