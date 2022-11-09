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

from __future__ import print_function

from tagRecommendation import TagRecommender
from communityDetection import CommunityDetector
from tagrecommendation_settings import RECOMMENDATION_DATA_DIR
from utils import loadFromJson
from numpy import load


class CommunityBasedTagRecommender():

    recommenders = None
    communityDetector = None
    dataProcessor = None
    #collections_ids = None
    dataset = None
    metric = None
    community_detection_heuristic = None
    classifier_type = None
    recommendation_heuristic = None
    classes = None

    def __init__(self,
                 dataset="",
                 classes=[],
                 metric="cosine",
                 community_detection_heuristic="ZeroInit",
                 recommendation_heuristic="hRankPercentage015",
                 classifier_type="bayes"):

        self.dataset = dataset
        self.classes = classes
        self.metric = metric
        self.community_detection_heuristic = community_detection_heuristic
        self.classifier_type = classifier_type
        self.recommendation_heuristic = recommendation_heuristic

    def load_recommenders(self):
        # Load classifier from file
        print("\nLOADING DATA FOR DATABASE %s AND CLASSES %s\n" % (self.dataset, ", ".join(self.classes)))
        print("Loading community detector...")
        self.communityDetector = CommunityDetector(verbose=False, PATH=RECOMMENDATION_DATA_DIR + "Classifier")
        print(self.communityDetector)

        # Loading class recommenders
        print("Loading class recommenders...")
        self.recommenders = dict()
        for class_name in self.classes:

            self.recommenders[class_name] = TagRecommender()
            self.recommenders[class_name].set_heuristic(self.recommendation_heuristic)

            data = {
                'TAG_NAMES': load(RECOMMENDATION_DATA_DIR + self.dataset + '_%s_SIMILARITY_MATRIX_' % class_name + self.metric + '_SUBSET_TAG_NAMES.npy'),
                'SIMILARITY_MATRIX': load(RECOMMENDATION_DATA_DIR + self.dataset + '_%s_SIMILARITY_MATRIX_' % class_name + self.metric + '_SUBSET.npy'),
            }

            self.recommenders[class_name].load_data(
                data=data,
                dataset="%s-%s" % (self.dataset, class_name),
                metric=self.metric
            )

            print(self.recommenders[class_name])

    def recommend_tags(self, input_tags, max_number_of_tags=None):
        com_name = self.communityDetector.detectCommunity(input_tags)
        rec = self.recommenders[com_name].recommend_tags(input_tags)

        return rec[0:max_number_of_tags], com_name
