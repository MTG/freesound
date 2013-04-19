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

import json,os,sys
from numpy import zeros
from tagrecommendation_settings import RECOMMENDATION_DATA_DIR


def saveToJson(path="", data="", verbose=True):
    with open(path, mode='w') as f:
        if verbose:
            print "Saving data to '" + path + "'"
        json.dump(data,f,indent=4)


def loadFromJson(path, verbose=False):
    with open(path, 'r') as f:
        if verbose:
            print "Loading data from '" + path + "'"
        return json.load(f)


def mtx2npy(M):
    n = M.shape[0]
    m = M.shape[1]
    npy = zeros((n, m), 'float32')

    non_zero_index = M.keys()
    done = 0
    for index in non_zero_index :
        npy[index[0]][index[1]] = M[index[0], index[1]]
        done += 1

    return npy


class Instance():
    id = None
    gt_class = None
    p_class = None
    fold = None

    def __init__(self, id, gt_class = None, p_class = None, fold = None):
        self.id = id
        self.gt_class = gt_class
        self.p_class = p_class
        self.fold = fold

    def serialize(self):
        return "%i,%i,%i,%i"%(self.id,
                              self.value_or_minusone(self.gt_class),
                              self.value_or_minusone(self.p_class),
                              self.value_or_minusone(self.fold))

    def value_or_minusone(self,value):
        if value is not None:
            return value
        else:
            return -1


class FSCollection:
    ids = None
    name = None
    verbose = None
    checked = None
    removed = None

    def __init__(self, name = "noname",load = True,verbose = True):
        self.ids = []
        self.removed = []
        self.checked = []
        self.name = name
        self.verbose = verbose


        if load:
            if os.path.exists(RECOMMENDATION_DATA_DIR + 'Collection %s.json'%self.name):
                self.load()

    def __str__(self):
        try:
            p = 100*float(len(list(set(self.ids).intersection(set(self.checked)))))/len(self.ids)
        except:
            p = 0.0
        return str('Collection: %s (%i sounds, %.2f%% checked, %i removed)'%(self.name,len(self.ids),p,len(self.removed)))

    def __repr__(self):
        try:
            p = 100*float(len(list(set(self.ids).intersection(set(self.checked)))))/len(self.ids)
        except:
            p = 0.0
        return '<Collection: %s, %i sounds, %.2f%% checked, %i removed>'%(self.name,len(self.ids),p,len(self.removed))

    def get_ids(self, MAX_PER_USER = None, MIN_TAGS = 1, LIMIT = None, RANDOMIZE = False, verbose = False):

        verbose = self.verbose

        sound_tags = loadFromJson(RECOMMENDATION_DATA_DIR + 'FREESOUND2012_RESOURCES_TAGS.json')
        resources_users = dict()
        if MAX_PER_USER:
            resources_users = loadFromJson(RECOMMENDATION_DATA_DIR + 'FREESOUND2012_RESOURCES_USER.json')

        all_ids = self.ids[:]
        valid_ids = []
        resources_per_user = dict()
        for count, id in enumerate(all_ids):

            if verbose:
                sys.stdout.write("\r\tChecking id %i of %i (%i accepted)" % (count,len(self.ids),len(valid_ids)))
                sys.stdout.flush()

            if not sound_tags.has_key(str(id)):
                continue

            if MIN_TAGS:
                if len(sound_tags[str(id)]) < MIN_TAGS:
                    continue

            if MAX_PER_USER:
                try:
                    user = resources_users[str(id)]
                    if resources_per_user.has_key(user):
                        resources_per_user[user] += 1
                    else:
                        resources_per_user[user] = 1

                    if resources_per_user[user] > MAX_PER_USER:
                        continue
                except:
                    continue

            valid_ids.append(id)

            if LIMIT:
                if len(valid_ids) >= LIMIT:
                    break

        if verbose:
            sys.stdout.write("\n")

        return valid_ids

    def get_tags(self):
        sound_tags = loadFromJson(RECOMMENDATION_DATA_DIR + 'FREESOUND2012_RESOURCES_TAGS.json')
        all_tags = []
        for id in self.ids:
            if not sound_tags.has_key(str(id)):
                continue
            all_tags += sound_tags[str(id)]

        return list(set(all_tags))

    def load(self, filename='Collection %s.json', append=False):
        if not append:
            if self.verbose:
                print "Loading from file: %s"%filename%self.name
            data = loadFromJson(RECOMMENDATION_DATA_DIR + filename%self.name)
            self.ids = data['ids']
            self.checked = data['checked']
            self.removed = data['removed']

        else:
            if self.verbose:
                print "Appending from file: %s"%filename%self.name
            data = loadFromJson(RECOMMENDATION_DATA_DIR + filename%self.name)
            self.ids.append(data['ids'])
            self.checked.append(data['checked'])
            self.removed.append(data['removed'])


class FSCollectionManager:
    collections = dict()
    verbose = None

    def __init__(self, collection_names, verbose=True):
        self.verbose = verbose
        for name in collection_names:
            key = len(self.collections.keys())
            self.collections[key] = FSCollection(name,verbose = verbose)
            if self.verbose:
                print self.collections[key]

    def save_collections(self):
        for key in self.collections.keys():
            self.collections[key].save(verbose=True)

    def display_names(self):
        for key in sorted(self.collections.keys()):
            print "\t%i: %s (%i sounds)" % (key,self.collections[key].name, len(self.collections[key].ids))

    def add_to_collection(self, col_id, object):
        self.collections[col_id].add(object)

    def check_valid_instances(self, MAX_PER_USER = None, MIN_TAGS=1, RANDOMIZE=True):
        for collection_key in self.collections:
            collection = self.collections[collection_key]
            valid_ids = collection.get_ids(MAX_PER_USER=MAX_PER_USER, MIN_TAGS=MIN_TAGS, RANDOMIZE=RANDOMIZE)

            print "\n%s"%collection
            print "\t%i valid sounds" % (len(valid_ids))

    def get_collections_ids(self, LIMIT=None, MAX_PER_USER=None, MIN_TAGS=1, RANDOMIZE=False, get_tags=False):
        output = dict()
        for id, collection in self.collections.items():
            tags = []
            if get_tags:
                tags = collection.get_tags()
            output[id] = {'ids': collection.get_ids(LIMIT=LIMIT, MAX_PER_USER=MAX_PER_USER, MIN_TAGS=MIN_TAGS, RANDOMIZE=RANDOMIZE, verbose=False),
                          'name': collection.name,
                          'tags': tags}

        return output
