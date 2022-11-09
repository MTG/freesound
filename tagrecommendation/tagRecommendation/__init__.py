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

from __future__ import absolute_import

from .heuristics import heuristics


class TagRecommender:
    """Class that implements an object that recommends tags"""

    heuristic = None
    data = None
    dataset = None
    metric = None

    def __init__(self):
        self.set_heuristic()

    def __repr__(self):
        if self.data:
            size = self.data['SIMILARITY_MATRIX'].shape[0]
        else:
            size = -1

        return "Tag Recommender (%s, %s, %s, %i tags)" % (self.heuristic['name'], self.dataset, self.metric, size)

    def set_heuristic(self, heuristic="hRankPercentage015"):

        if type(heuristic) == str:
            self.heuristic = heuristics[heuristic].copy()
        elif type(heuristic) == dict:
            self.heuristic = heuristic
        else:
            raise Exception("Wrong heuristic given")

    def load_data(self, dataset=None, metric=None, data=None):
        self.data = data
        self.dataset = dataset
        self.metric = metric

    def recommend_tags(self, input_tags=None):

        if not input_tags:
            raise Exception("No input tags specified")
        if not self.heuristic:
            raise Exception("No heuristic specified (use 'set_heuristic()')")
        if not self.data:
            raise Exception("No data has been loaded (use 'load_data()')")

        # Prepare variables
        chooseAlgorithm = self.heuristic['c']
        aggregateAlgorithm = self.heuristic['a']
        selectAlgorithm = self.heuristic['s']

        # CHOOSE candidate tags
        candidate_tags = chooseAlgorithm(input_tags, self.data['TAG_NAMES'], self.data['SIMILARITY_MATRIX'], self.heuristic['options'])

        # AGGREGATE candidate tags
        aggregated_candiate_tags, aggregated_candiate_tags_list = aggregateAlgorithm(candidate_tags, input_tags, self.heuristic['options'])

        # SELECT the number of tags to recommend
        if len(aggregated_candiate_tags_list) > 1:
            added_tags = selectAlgorithm(aggregated_candiate_tags_list, aggregated_candiate_tags, input_tags, self.heuristic['options'])
        else:
            if len(aggregated_candiate_tags_list) == 1:
                added_tags = list()
                added_tags.append(aggregated_candiate_tags_list[0]['name'])
            else:
                added_tags = list()

        return added_tags
