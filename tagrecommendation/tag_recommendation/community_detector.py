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

import os
from builtins import object
from builtins import str

from numpy import load, where, zeros
from sklearn.externals import joblib

from utils import loadFromJson
from tagrecommendation_settings import RECOMMENDATION_DATA_DIR


class CommunityDetector(object):
    verbose = None
    clf = None
    clf_type = None
    class_name_ids = None
    n_training_instances = None
    init_method = None
    selected_instances = None
    tag_names = None

    def __init__(self, verbose=True, classifier_type="svm", PATH=None, INIT_METHOD="ZeroInit", selected_instances=None):

        self.verbose = verbose
        self.n_training_instances = 0
        self.clf_type = classifier_type
        self.class_name_ids = dict()
        self.init_method = INIT_METHOD
        self.selected_instances = selected_instances

        if not os.path.exists(PATH + ".pkl") or \
                not os.path.exists(PATH + "_meta.json") or \
                not os.path.exists(RECOMMENDATION_DATA_DIR + 'Classifier_TAG_NAMES.npy'):
            raise Exception("Classifier not existing in classifiers folder.")

        self.clf = joblib.load(PATH + ".pkl")
        meta = loadFromJson(PATH + "_meta.json")
        self.clf_type = meta['clf_type']
        self.class_name_ids = meta['class_name_ids']
        self.n_training_instances = meta['n_training_instances']
        self.tag_names = load(RECOMMENDATION_DATA_DIR + 'Classifier_TAG_NAMES.npy')

    def __repr__(self):
        return "Community Detector (%s, %i classes, %i instances, %s init) " % (
            self.clf_type, len(self.class_name_ids.keys()), self.n_training_instances, self.init_method
        )

    def load_instance_vector_from_tags(self, tags):
        tags_t = tags[:]

        instance_vector = zeros(len(self.tag_names))
        for tag in tags_t:
            w_out = where(self.tag_names == tag)[0]
            if len(w_out) > 0:
                pos = w_out[0]
                instance_vector[pos] = 1
        return instance_vector

    def detectCommunity(self, input_tags=None):
        if not self.clf:
            raise Exception("Classifier not yet trained!")
        instance_vector = self.load_instance_vector_from_tags(input_tags)
        cl = self.clf.predict([instance_vector])[0]

        return str(self.class_name_ids[str(cl)])
