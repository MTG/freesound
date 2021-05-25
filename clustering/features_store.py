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

import json
import logging
import os

import clustering_settings as clust_settings
import numpy as np
import redis
from django.conf import settings

logger = logging.getLogger('clustering')


class RedisStore(object):
    def __init__(self):
        self.r = redis.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.AUDIO_FEATURES_REDIS_STORE_ID)

    def set_feature(self, sound_id, feature):
        self.r.set(str(sound_id), json.dumps(feature))

    def get_feature(self, sound_id):
        feature = self.r.get(str(sound_id))
        if feature:
            return json.loads(feature)

    def set_features(self, d):
        self.r.mset({k: json.dumps(v) for k, v in d.iteritems()})

    def get_features(self, sound_ids):
        return self.r.mget(sound_ids)


class FeaturesStore(object):
    """Method for storing and retrieving audio features
    """
    def __init__(self):
        self.redis = RedisStore()
        self.__load_features()

    def __load_features(self):
        self.AS_features = json.load(open(os.path.join(
            clust_settings.INDEX_DIR, 
            clust_settings.AVAILABLE_FEATURES[clust_settings.DEFAULT_FEATURES]['DATASET_FILE']
        ), 'r'))
        self.redis.set_features(self.AS_features)

    def return_features(self, sound_ids):
        features = []
        sound_ids_out = []
        output = self.redis.get_features(sound_ids)
        for sound_id, feature in zip(sound_ids, output):
            if feature:
                features.append(json.loads(feature))
                sound_ids_out.append(sound_id)
            
        return np.array(features).astype('float32'), sound_ids_out
