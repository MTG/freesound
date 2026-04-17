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
import joblib

class CommunityDetector(object):
    clf = None

    def __init__(self, PATH=None,):
        if not os.path.exists(PATH + ".joblib"):
            raise Exception(f"Classifier not existing in classifiers folder ({PATH}).")
        self.clf = joblib.load(PATH + ".joblib")

   
    def detectCommunity(self, input_tags=None):
        if not self.clf:
            raise Exception("Classifier not yet trained!")    
        return self.clf.predict([" ".join(input_tags)])[0]

