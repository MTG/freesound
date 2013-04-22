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

import logging, traceback
from tagrecommendation.client import TagRecommendation

logger = logging.getLogger('web')


def get_recommended_tags(input_tags, max_number_of_tags=None, general_recommendation=False):

    try:
        recommended_tags = TagRecommendation.recommend_tags(input_tags,
                                                            max_number_of_tags=max_number_of_tags,
                                                            general_recommendation=general_recommendation)
    except Exception, e:
        logger.debug('Could not get a response from the tagrecommendation service (%s)\n\t%s' % \
                     (e, traceback.format_exc()))
        recommended_tags = False

    return recommended_tags['tags'], recommended_tags['community']

