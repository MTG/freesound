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


from tagRecommendation import TagRecommender
from dataProcessing import DataProcessor
from communityDetection import CommunityDetector
from tagrecommendation_settings import RECOMMENDATION_DATA_DIR, CLASSES, USE_COMMUNITY_BASED_RECOMMENDERS
from utils import loadFromJson, FSCollectionManager
from numpy import load


class CommunityBasedTagRecommender():

    recommenders = None
    communityDetector = None
    dataProcessor = None
    collections_ids = None
    dataset = None
    metric = None
    community_detection_heuristic = None
    classifier_type = None
    recommendation_heuristic = None

    def __init__(self,
                 dataset="FREESOUND2012",
                 metric="cosine",
                 community_detection_heuristic="ZeroInit",
                 recommendation_heuristic="hRankPercentage015",
                 classifier_type="bayes"):

        self.dataset = dataset
        self.metric = metric
        self.community_detection_heuristic = community_detection_heuristic
        self.classifier_type = classifier_type
        self.recommendation_heuristic = recommendation_heuristic

        collections = [col[11:-5] for col in CLASSES.values()]
        fcm = FSCollectionManager(collections, verbose=False)
        self.collections_ids = fcm.get_collections_ids(get_tags=True)

    def load_recommenders(self):
        # Load classifier from file
        print "Loading community detector..."
        self.communityDetector = CommunityDetector(verbose=False, PATH=RECOMMENDATION_DATA_DIR + "Classifier")
        print self.communityDetector

        print "Loading recommenders..."

        # Load general recommender
        self.recommenders = dict()
        self.recommenders[-1] = TagRecommender()
        self.recommenders[-1].set_heuristic(self.recommendation_heuristic)
        data = {
            'TAG_NAMES': load(RECOMMENDATION_DATA_DIR + self.dataset + '_SIMILARITY_MATRIX_' + self.metric + '_TAG_NAMES.npy'),
            'SIMILARITY_MATRIX': load(RECOMMENDATION_DATA_DIR + self.dataset + '_SIMILARITY_MATRIX_' + self.metric + '.npy'),
        }
        self.recommenders[-1].load_data(
            data=data,
            dataset="FREESOUND2012-General",
            metric=self.metric
        )
        print self.recommenders[-1]

        if USE_COMMUNITY_BASED_RECOMMENDERS:
            # Load particular recommenders
            for collection_id, collection_data in self.collections_ids.items():
                self.recommenders[collection_id] = TagRecommender()
                self.recommenders[collection_id].set_heuristic(self.recommendation_heuristic)

                data = {
                    'TAG_NAMES': load(RECOMMENDATION_DATA_DIR + self.dataset + '_%s_SIMILARITY_MATRIX_' % collection_data['name'] + self.metric + '_SUBSET_TAG_NAMES.npy'),
                    'SIMILARITY_MATRIX': load(RECOMMENDATION_DATA_DIR + self.dataset + '_%s_SIMILARITY_MATRIX_' % collection_data['name'] + self.metric + '_SUBSET.npy'),
                }

                self.recommenders[collection_id].load_data(
                    data=data,
                    dataset="FREESOUND2012-%s" % collection_data['name'],
                    metric=self.metric
                )

                print self.recommenders[collection_id]

    def recompute_recommenders(self, LIMIT=None):

        # Load community detectors
        print "Loading community detector..."
        self.communityDetector = CommunityDetector(
            verbose=True,
            LIMIT=LIMIT,
            MAX_PER_USER=None,
            MIN_TAGS=1,
            RANDOMIZE=True,
            classifier_type=self.classifier_type,
            PATH=None,
            INIT_METHOD=self.community_detection_heuristic,
        )
        # Save community detector
        print self.communityDetector
        self.communityDetector.save_clf(filename="Classifier.saved")

        # Load needed data and processor
        print "\nLoading data processor..."
        self.dataProcessor = DataProcessor(verbose=True)
        print self.dataProcessor
        resource_class = loadFromJson(RECOMMENDATION_DATA_DIR + 'FREESOUND2012_RESOURCES_CLASS.json')
        instances_ids = resource_class.keys()

        # Load general recommender
        print "\nLoading general recommender..."
        self.recommenders = dict()
        self.recommenders[-1] = TagRecommender()
        self.recommenders[-1].set_heuristic(self.recommendation_heuristic)
        data_general_recommender = self.dataProcessor.association_matrix_to_similarity_matrix(
            dataset=self.dataset,
            training_set=instances_ids[0:LIMIT],
            save_sim=True,
            is_general_recommender=True,
        )
        self.recommenders[-1].load_data(data=data_general_recommender, dataset=self.dataset, metric=self.metric)
        print self.recommenders[-1]

        # Load specific recommenders (depend on community recommendation mode)
        print "\nLoading community recommenders..."
        instance_id_class = []
        for count, instance_id in enumerate(instances_ids):
            class_id = resource_class[instance_id]
            instance_id_class.append([instance_id, class_id])

        for collection_id, collection_data in self.collections_ids.items():
            self.recommenders[collection_id] = TagRecommender()
            self.recommenders[collection_id].set_heuristic(self.recommendation_heuristic)

            # All resources from the training set classified as the selected category
            # (instead of all manually labeled)
            training_ids = []
            for instance in instance_id_class:
                if instance[1] == collection_id:
                    training_ids.append(instance[0])
            # Add limit
            training_ids = training_ids[0:LIMIT]

            if len(training_ids) < 1:
                raise Exception("Too less training ids for collection %s" % collection_data['name'])

            data = self.dataProcessor.association_matrix_to_similarity_matrix(
                dataset=self.dataset,
                training_set=training_ids,
                save_sim=True,
                out_name_prefix=collection_data['name'],
                is_general_recommender=False,
            )
            self.recommenders[collection_id].load_data(
                data=data,
                dataset="FREESOUND2012-%s" % collection_data['name'],
                metric=self.metric
            )
            print self.recommenders[collection_id]


    def recommend_tags(self, input_tags, general_recommendation=False):
        if general_recommendation or not USE_COMMUNITY_BASED_RECOMMENDERS:
            com_name = ""
            rec = self.recommenders[-1].recommend_tags(input_tags)
        else:
            com_id, com_name = self.communityDetector.detectCommunity(input_tags)
            rec = self.recommenders[com_id].recommend_tags(input_tags)

        return rec, com_name