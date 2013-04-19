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


'''
This methods computes the similarity matrix and classifiers needed for the tag recommendation
service to run. Once they are computed, these can be loaded quickly and you're done.
However, to compute these matrixs and stuff it needs from some other precomputed files
that need to be derived from the freesound DB. It is still pending to write the function to
compute this files. The needed files are: (some of them might not be strictly needed)

Collection XXX .json
ASSOCIATION_MATRIX.mtx
RESOURCE_IDS.npy
RESOURCES_CLASS.json
RESOURCES_TAGS.json* ??
RESOURCES_USER.json
TAG_IDS.npy

'''

from communityBasedTagRecommendation import CommunityBasedTagRecommender

cbtr = CommunityBasedTagRecommender()
cbtr.recompute_recommenders(LIMIT=100)
