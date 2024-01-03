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

import operator

from numpy import *


def cNMostSimilar(input_tags, tag_names, similarity_matrix, options):

    N = options['cNMostSimilar_N']
    unicode_tag_names = [t.decode('utf-8') for t in tag_names]
    candidate_tags = []
    for tag in input_tags:
        # Check that tag exists in the tag matrix, if it does not exist we cannot recommend similar tags
        if tag in unicode_tag_names:
            # Find N most similar tags in the row
            idx = unicode_tag_names.index(tag)
            #where(tag_names == tag)[0][0]
            row_idx = nonzero(similarity_matrix[idx, :])
            row_idx = row_idx[0]
            row = similarity_matrix[idx, row_idx]
            MAX = N
            most_similar_idx = row.argsort(
            )[-MAX - 1:-1
              ][::-1
                ]    # We pick the first N most similar tags (practically the same as no threshold but more efficient)
            most_similar_dist = row[most_similar_idx]
            most_similar_tags = tag_names[row_idx[most_similar_idx]]

            rank = N
            for count, item in enumerate(most_similar_tags):
                if item not in input_tags:
                    candidate_tags.append({'name': item, 'rank': rank, 'dist': most_similar_dist[count], 'from': tag})
                    rank -= 1
                else:
                    pass    # recommended tag was already present in input tags
        else:
            pass    # If tag does not exist we do not recommend anything. Maybe we could do something else here

    return candidate_tags


def aNormalizedRankSum(candidate_tags, input_tags, options):

    factor = options['aNormalizedRankSum_factor']

    candidate_tags.sort(key=operator.itemgetter('rank'))
    candidate_tags.reverse()

    aggregated_candiate_tags = {}
    for item in candidate_tags:
        if item['name'] in aggregated_candiate_tags:    # Item already there
            aggregated_candiate_tags[
                item['name']
            ] = (aggregated_candiate_tags[item['name']] + float(item['rank']) / (len(input_tags))) * factor
        else:
            aggregated_candiate_tags[item['name']] = float(item['rank']) / (len(input_tags))
    aggregated_candiate_tags_list = []
    for key in aggregated_candiate_tags.keys():
        aggregated_candiate_tags_list.append({"name": key, "rank": aggregated_candiate_tags[key]})
    aggregated_candiate_tags_list.sort(key=operator.itemgetter('rank'))
    aggregated_candiate_tags_list.reverse()

    return aggregated_candiate_tags, aggregated_candiate_tags_list


def sThreshold(aggregated_candiate_tags_list, aggregated_candiate_tags, input_tags, options, threshold=None):

    if not threshold:
        threshold = options['sThreshold_threshold']

    recommended_tags = []
    for item in aggregated_candiate_tags_list:
        if item['rank'] >= threshold:
            recommended_tags.append(item)

    added_tags = []
    for item in recommended_tags:
        added_tags.append(item['name'])

    return added_tags


def sPercentage(aggregated_candiate_tags_list, aggregated_candiate_tags, input_tags, options):

    percentage = options['sPercentage_percentage']
    max_score = aggregated_candiate_tags_list[0]['rank']
    threshold = max_score * (1.0 - percentage)
    return sThreshold(aggregated_candiate_tags_list, aggregated_candiate_tags, input_tags, options, threshold)
