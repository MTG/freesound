import logging
import os
import sys
import time
import yaml
from django.conf import settings

from gaia2 import DataSet, View, DistanceFunctionFactory

from clustering_settings import clustering_settings as clust_settings

# for re-using gaia similarity dataset
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from similarity.gaia_wrapper import GaiaWrapper as GaiaWrapperSimilarity

logger = logging.getLogger('clustering')


class GaiaWrapperClustering:
    """Gaia wrapper for the clustering engine.

    This class contains helper methods to interface with Gaia.    
    """
    def __init__(self):
        self.as_dataset = None
        self.tag_dataset = None
        self.fs_dataset = None
        self.ac_dataset = None
        self.gaia_similiarity = None

        self.index_path = clust_settings.get('INDEX_DIR')

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
        return os.path.join(clust_settings.get('INDEX_DIR'), ds_name + '.db')

    def __load_datasets(self):
        # Could avoid code repetition here by creating an abstracted function for creating gaia DS, view & metric
        if clust_settings.get('INDEX_NAME_AS', None):
            self.as_dataset = DataSet()
            self.as_dataset.load(self.__get_dataset_path(clust_settings.get('INDEX_NAME_AS')))
            self.as_view = View(self.as_dataset)
            # metrics here can be 'euclidean', 'CosineSimilarity', 'CosineAngle', 'CosineAngle'
            self.as_metric = DistanceFunctionFactory.create('euclidean', self.as_dataset.layout(), 
                {'descriptorNames': 'AS_embeddings_ppc_max_energy'})

        if clust_settings.get('INDEX_NAME_TAG', None):
            self.tag_dataset = DataSet()
            self.tag_dataset.load(self.__get_dataset_path(clust_settings.get('INDEX_NAME_TAG')))
            self.tag_view = View(self.tag_dataset)
            self.tag_metric = DistanceFunctionFactory.create('euclidean', self.tag_dataset.layout())

        if clust_settings.get('INDEX_NAME_FS', None):
            self.fs_dataset = DataSet()
            self.fs_dataset.load(self.__get_dataset_path(clust_settings.get('INDEX_NAME_FS')))
            self.fs_view = View(self.fs_dataset)
            self.fs_metric = DistanceFunctionFactory.create('euclidean', self.fs_dataset.layout(), {'descriptorNames': 'pca'})
        
        if clust_settings.get('INDEX_NAME_AC', None):
            self.__load_ac_descriptors_dataset()

        if clust_settings.get('FS_SIMILARITY', False):
            self.gaia_similiarity = GaiaWrapperSimilarity()

    def __load_ac_descriptors_dataset(self):
        self.ac_dataset = DataSet()
        self.ac_dataset.load(self.__get_dataset_path(clust_settings.get('INDEX_NAME_AC')))
        self.ac_view = View(self.ac_dataset)
        self.ac_metric = DistanceFunctionFactory.create('euclidean', self.ac_dataset.layout(), 
            {'descriptorNames': [
                'ac_brightness', 
                'ac_boominess', 
                'ac_depth', 
                'ac_hardness', 
                'ac_roughness', 
                'ac_sharpness', 
                'ac_warmth'
            ]})

    def search_nearest_neighbors(self, sound_id, k, in_sound_ids=[], features='audio_as'):
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
        for sound_id in sound_ids:
            try:
                tag_features.append(self.tag_dataset.point(sound_id).value('tags_lda'))
            except Exception as e:
                #logger.info(e)
                tag_features.append(None)
        return tag_features
