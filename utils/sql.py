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

from django.db import connection

class DelayedQueryExecuter:
    """ The delayed executed executes a query, but waits for the first time
    the results are actually needed, i.e. via iteration """
    def __init__(self, query):
        self.query = query
        self.cache = None
    
    def __iter__(self):
        if self.cache is None:
            cursor = connection.cursor() #@UndefinedVariable
            cursor.execute(self.query)
            
            column_names = [desc[0] for desc in cursor.description]
            
            # cursor.fetchall fetches all results in one go (i.e. not a generator) so this is just as fast
            self.cache = [dict(zip(column_names, row)) for row in cursor.fetchall()]

        for row in self.cache:
            yield row