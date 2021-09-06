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

from celery.decorators import task

@task(name="process_analysis_results")
def process_analysis_results(sound_id, analyzer):
    print('Processing analysis results for sound sound {} after analyzer {}'.format(sound_id, analyzer))
    import time
    time.sleep(2)
    print('Done processing analysis results for sound sound {} after analyzer {}'.format(sound_id, analyzer))
