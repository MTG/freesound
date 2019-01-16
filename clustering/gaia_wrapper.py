import logging
import os
import time

import yaml
from gaia2 import DataSet, View, DistanceFunctionFactory


class GaiaWrapper:
    def __init__(self):
        self.dataset = DataSet()
        self.view = None
        self.metric = None
        self.__load_dataset()

    def __load_dataset(self):
        self.dataset.load('FS_6k_sounds_normalized.db')  # TODO: put this filename in config
        self.view = View(self.dataset)
        self.metric = DistanceFunctionFactory.create('euclidean', self.dataset.layout())

    def search_nearest_neighbors(self, sound_id, k, in_sound_ids):
        filter = 'WHERE point.id IN ("' + '", "'.join(in_sound_ids) + '")'
        return self.view.nnSearch(sound_id, self.metric, filter).get(k)[1:]
