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

from tagrecommendation_settings import RECOMMENDATION_DATA_DIR
from utils import mtx2npy
from numpy import where, in1d, load, save
from pysparse.sparse import spmatrix
from math import sqrt


class DataProcessor:
    """Class that implements operations to do with data"""

    verbose = None

    def __init__(self, verbose=False):
        self.verbose = verbose

    def __repr__(self):
        return "DataProcessor instance"

    def association_matrix_to_similarity_matrix(self,
                                                metric="cosine",
                                                dataset="FREESOUND2012",
                                                save_sim=False,
                                                training_set=None,
                                                out_name_prefix = "",
                                                is_general_recommender = False):
        """Given an association matrix"""

        if self.verbose:
            print "Loading association matrix and tag names, ids files..."
        try:
            M = spmatrix.ll_mat_from_mtx(RECOMMENDATION_DATA_DIR + dataset + "_ASSOCIATION_MATRIX.mtx")
            resource_ids = load(RECOMMENDATION_DATA_DIR + dataset + "_RESOURCE_IDS.npy")
            tag_names = load(RECOMMENDATION_DATA_DIR + dataset + "_TAG_NAMES.npy")
        except Exception:
            raise Exception("Error loading association matrix and tag names, ids data")

        if metric not in ['cosine','binary','coocurrence','jaccard']:
            raise Exception("Wrong similarity metric specified")

        if training_set:
            if self.verbose:
                print "Computing similarity matrix from a resource subset of the whole association matrix..."
            # Get index of resources to train (usable index for M)
            resource_id_positions = where(in1d(resource_ids, training_set, assume_unique=True))[0]

            # Matrix multiplication (only taking in account resources in training set and ALL tags)
            MM = spmatrix.dot(M[resource_id_positions, :], M[resource_id_positions, :])

            # Get similarity matrix
            sim_matrix = spmatrix.ll_mat(MM.shape[0],MM.shape[0])
            non_zero_index = MM.keys()
            for index in non_zero_index:
                if metric == 'cosine':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]] * (1 / (sqrt(MM[index[0], index[0]]) * sqrt(MM[index[1], index[1]])))
                elif metric == 'coocurrence':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]]
                elif metric == 'binary':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]]/MM[index[0], index[1]]
                elif metric == 'jaccard':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]] * (1 / (MM[index[0], index[0]] + MM[index[1], index[1]] - MM[index[0], index[1]]))

            # Clean out similarity matrix (clean tags that are not used)
            tag_positions = []
            for i in range(0, sim_matrix.shape[0]):
                if sim_matrix[i, i] != 0.0:
                    tag_positions.append(i)

            # Transform sparse similarity matrix to npy format
            sim_matrix_npy = mtx2npy(sim_matrix[tag_positions,tag_positions])
            tag_names_sim_matrix = tag_names[tag_positions]

            if save_sim:
                if not is_general_recommender:
                    # Save sim
                    path = RECOMMENDATION_DATA_DIR + dataset + "_%s_SIMILARITY_MATRIX_" % out_name_prefix + metric + "_SUBSET.saved.npy"
                    if self.verbose:
                        print "Saving to " + path + "..."
                    save(path, sim_matrix_npy)

                    # Save tag names
                    path = RECOMMENDATION_DATA_DIR + dataset + "_%s_SIMILARITY_MATRIX_" % out_name_prefix + metric + "_SUBSET_TAG_NAMES.saved.npy"
                    if self.verbose:
                        print "Saving to " + path + "..."
                    save(path, tag_names_sim_matrix)
                else:
                    # Save sim
                    path = RECOMMENDATION_DATA_DIR + dataset + "_SIMILARITY_MATRIX_" + metric + ".saved.npy"
                    if self.verbose:
                        print "Saving to " + path + "..."
                    save(path, sim_matrix_npy)

                    # Save tag names
                    path = RECOMMENDATION_DATA_DIR + dataset + "_SIMILARITY_MATRIX_" + metric + "_TAG_NAMES.saved.npy"
                    if self.verbose:
                        print "Saving to " + path + "..."
                    save(path, tag_names_sim_matrix)


        else:
            if self.verbose:
                print "Computing similarity matrix from the whole set of resources..."

            # Matrix multiplication
            MM = spmatrix.dot(M,M)

            # Create similarity matrix
            sim_matrix = spmatrix.ll_mat(MM.shape[0],MM.shape[0])
            non_zero_index = MM.keys()
            for index in non_zero_index:
                if metric == 'cosine':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]] * (1 / (sqrt(MM[index[0], index[0]]) * sqrt(MM[index[1], index[1]])))
                elif metric == 'coocurrence':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]]
                elif metric == 'binary':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]]/MM[index[0], index[1]]
                elif metric == 'jaccard':
                    sim_matrix[index[0], index[1]] = MM[index[0], index[1]] * (1 / (MM[index[0], index[0]] + MM[index[1], index[1]] - MM[index[0], index[1]]))

            sim_matrix_npy = mtx2npy(sim_matrix)
            tag_names_sim_matrix = tag_names

            if save_sim:
                # Save sim
                path = RECOMMENDATION_DATA_DIR + dataset + "_SIMILARITY_MATRIX_" + metric + ".saved.npy"
                if self.verbose:
                    print "Saving to " + path + "..."
                save(path, sim_matrix_npy)

                # Save tag names
                path = RECOMMENDATION_DATA_DIR + dataset + "_SIMILARITY_MATRIX_" + metric + "_TAG_NAMES.saved.npy"
                if self.verbose:
                    print "Saving to " + path + "..."
                save(path, tag_names_sim_matrix)

        return {'SIMILARITY_MATRIX': sim_matrix_npy, 'TAG_NAMES': tag_names_sim_matrix}




