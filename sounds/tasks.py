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


@task(name='sounds.analyze_method1')
def analyze_method1(sound_id):
    print('Analyzing sound {} with method 1'.format(sound_id))
    import time
    time.sleep(1)
    print('Done analyzing sound {} with method 1'.format(sound_id))


@task(name='analysis_method1.analyze_method2')
def analyze_method2(sound_id):
    print('Analyzing sound {} with method 2'.format(sound_id))
    import time
    time.sleep(1)
    print('Done analyzing sound {} with method 2'.format(sound_id))
