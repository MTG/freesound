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

from sklearn import svm, tree, ensemble, naive_bayes
from sklearn.externals import joblib
from numpy import load, where, zeros
from utils import Instance, saveToJson, loadFromJson, FSCollection
from tagrecommendation_settings import RECOMMENDATION_DATA_DIR, CLASSES
import datetime
import sys,os


class ClassifierUtils():

    sound_tags = None
    tag_names = None
    N_TAGS = None
    dataset = None
    precomputed_instances = None
    classifier_type = None

    def __init__(self, dataset="FREESOUND2012", classifier_type="bayes"):

        self.dataset = dataset
        self.sound_tags = loadFromJson(RECOMMENDATION_DATA_DIR + self.dataset + '_RESOURCES_TAGS.json')
        self.tag_names = load(RECOMMENDATION_DATA_DIR + self.dataset + '_TAG_NAMES.npy')
        self.N_TAGS = len(self.tag_names)
        self.precomputed_instances = dict()
        self.classifier_type = classifier_type

    def get_instance_vector_from_tags(self, tags):
        instance_vector = zeros(self.N_TAGS)
        for tag in tags:
            try:
                pos = int(where(self.tag_names == tag)[0][0])
                instance_vector[pos] = 1
            except Exception:
                pass

        return instance_vector

    def get_instance_vector_from_resource_id(self, id):
        if id not in self.precomputed_instances:
            raise Exception("No instance vector for resource with id %i" % id)
        else:
            return self.precomputed_instances[id]

    def preload_instance_vectors(self, instances, verbose=True):

        if verbose:
            print "Preloading instance vectors..."
        sys.stdout.flush()
        self.precomputed_instances = dict()
        i = 0
        for instance in instances:
            i += 1
            if verbose:
                sys.stdout.write("\r\tLoading instance %i of %i..." % (i, len(instances)))
                sys.stdout.flush()

            self.precomputed_instances[instance.id] = self.load_instance_vector_from_resource_id(instance.id)

        sys.stdout.write("\n")

    def load_instance_vector_from_resource_id(self, id=None, tags=None):

        if not tags:
            tags_t = self.sound_tags[str(id)]
        else:
            tags_t = tags[:]

        instance_vector = zeros(self.N_TAGS)
        for tag in tags_t:
            w_out = where(self.tag_names == tag)[0]
            if len(w_out) > 0:
                pos = w_out[0]
                instance_vector[pos] = 1
        return instance_vector

    def load_instance_vector_from_tags(self, tags):
        return self.load_instance_vector_from_resource_id(tags = tags)


class CommunityDetector:
    verbose = None
    clf = None
    clf_type = None
    class_name_ids = None
    n_training_instances = None
    init_method = None
    selected_instances = None

    def __init__(self,
                 verbose=True,
                 LIMIT=20,
                 MAX_PER_USER=25,
                 MIN_TAGS=4,
                 RANDOMIZE=False,
                 classifier_type="svm",
                 PATH=None,
                 INIT_METHOD="ZeroInit",
                 selected_instances=None
                 ):

        self.verbose = verbose
        self.n_training_instances = 0
        self.clf_type = classifier_type
        self.class_name_ids = dict()
        self.init_method = INIT_METHOD
        self.selected_instances = selected_instances
        self.cu = ClassifierUtils()
        self.cu.classifier_type = classifier_type

        if not PATH:
            self.load(LIMIT = LIMIT, MAX_PER_USER = MAX_PER_USER, MIN_TAGS = MIN_TAGS, RANDOMIZE = RANDOMIZE, classifier_type = classifier_type)

        else:
            if not os.path.exists(PATH + ".pkl") or not os.path.exists(PATH + "_meta.json"):
                raise Exception("Classifier not existing in classifiers folder.")

            self.clf = joblib.load(PATH + ".pkl")
            meta = loadFromJson(PATH + "_meta.json")
            self.clf_type = meta['clf_type']
            self.class_name_ids = meta['class_name_ids']
            self.n_training_instances = meta['n_training_instances']

    def __repr__(self):
        return "Community Detector (%s, %i classes, %i instances, %s init) " % (self.clf_type,len(self.class_name_ids.keys()),self.n_training_instances, self.init_method)

    def load(self, LIMIT = 20, MAX_PER_USER = 25, MIN_TAGS = 4, RANDOMIZE = False, classifier_type = "svm"):

        classes = CLASSES
        all_instances = []
        class_name_ids = dict()
        collections = dict()

        for key in classes.keys():
            class_id = len(class_name_ids.keys())
            class_name_ids[class_id] = key
            collections[class_id] = FSCollection(classes[key][11:-5], verbose=self.verbose)
        self.class_name_ids = class_name_ids

        minimum = 99999999
        min_class = "-"
        if self.verbose:
            print "Calculating maximum number of resources...",
        for class_id, collection in collections.items():
            N = len(collection.get_ids(MAX_PER_USER = MAX_PER_USER, MIN_TAGS = MIN_TAGS, LIMIT = LIMIT, RANDOMIZE = RANDOMIZE, verbose=False))
            if N < minimum:
                minimum = N
                min_class = class_id
        FIXED_LIMIT = min(minimum, LIMIT or 99999999)
        if self.verbose:
            print "Fixed limit to %i samples from collection %s"%(FIXED_LIMIT,min_class)

        if self.verbose:
            print "Getting resources data...",
        for class_id, collection in collections.items():
            class_instance_ids = collection.get_ids(MAX_PER_USER = MAX_PER_USER, MIN_TAGS = MIN_TAGS, LIMIT = FIXED_LIMIT, RANDOMIZE = RANDOMIZE)
            for id in class_instance_ids:
                all_instances.append(Instance(id = int(id), gt_class=class_id))

        if self.verbose:
            print "%i instances selected from %i distinct classes"%(len(all_instances),len(class_name_ids.keys()))
        # Free memory for collections:
        collections = None

        instances = all_instances
        self.cu.preload_instance_vectors(instances, verbose=self.verbose)

        if self.verbose:
            print "Training classifier..."
        self.cu.classifier_type = classifier_type
        loaded_instances = []
        classes = []
        verbose = self.verbose
        i = 0
        for instance in instances:
            i += 1
            if verbose:
                sys.stdout.write("\r\tLoading instance %i of %i..." % (i, len(instances)))
                sys.stdout.flush()
            resource_id = instance.id
            class_id = instance.gt_class
            instance_vector = self.cu.get_instance_vector_from_resource_id(resource_id)
            loaded_instances.append(list(instance_vector))
            classes.append(class_id)

        if verbose:
            sys.stdout.write("\n\tFitting classifier with %i instances...\n" % len(loaded_instances))
            sys.stdout.flush()

        if self.cu.classifier_type == "svm":
            clf = svm.LinearSVC()
        elif self.cu.classifier_type == "tree":
            clf = tree.DecisionTreeClassifier()
        elif self.cu.classifier_type == "etree":
            clf = ensemble.RandomForestClassifier(n_estimators=10)
        elif self.cu.classifier_type == "bayes":
            clf = naive_bayes.BernoulliNB()
        else:
            raise Exception("No valid classifier type was specified!")

        clf.fit(loaded_instances,classes)
        self.clf = clf
        print ""

        self.n_training_instances = len(instances)

    def save_clf(self, filename=None):
        if not self.clf:
            raise Exception("Classifier not yet trained!")

        if not filename:
            filename = RECOMMENDATION_DATA_DIR + "%s_%i_%i-%i_%i-%i"%(self.clf_type,self.n_training_instances,datetime.datetime.today().day,datetime.datetime.today().month,datetime.datetime.today().hour,datetime.datetime.today().minute)
        else:
            filename = RECOMMENDATION_DATA_DIR + filename

        if self.verbose:
            print "Saving classifier to %s [.pkl | _meta.json]"%filename

        joblib.dump(self.clf, filename + ".pkl", compress=9)
        saveToJson(filename + "_meta.json", {'clf_type': self.clf_type,
                                             'class_name_ids': self.class_name_ids,
                                             'n_training_instances': self.n_training_instances}, verbose=False)

    def detectCommunity(self, input_tags=None):
        if not self.clf:
            raise Exception("Classifier not yet trained!")
        instance_vector = self.cu.load_instance_vector_from_tags(input_tags)
        cl = self.clf.predict([instance_vector])[0]

        return cl, str(self.class_name_ids[unicode(cl)])