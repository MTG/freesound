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
import graypy
import logging
import json
from tag_recommendation.community_tag_recommender import CommunityBasedTagRecommender

from flask import Flask, jsonify, request

app = Flask(__name__)


GRAYLOG_HOST = os.environ.get("GRAYLOG_HOST_ENV", None)
GRAYLOG_PORT = os.environ.get("GRAYLOG_PORT_ENV", None)
DATA_DIR = os.environ.get("TAG_RECOMMENDATION_MODELS_DIR", "/tag_recommendation_models/")  
LOG_TO_GRAYLOG = os.environ.get("LOG_TO_GRAYLOG", "False").lower() in ("true", "1", "t")


tag_recommendation_data_settings = json.load(open(os.path.join(DATA_DIR, "tag_recommendation_data_settings.json"), 'r'))
tag_recommender = CommunityBasedTagRecommender(
    base_data_dir=DATA_DIR,
    dataset=tag_recommendation_data_settings['database'], 
    classes=tag_recommendation_data_settings['classes'])
tag_recommender.load_recommenders()


class GraylogLogFilter(logging.Filter):

    def filter(self, record):
        try:
            message = record.getMessage()
            json_part = message[message.find('(') + 1:-1]
            fields = json.loads(json_part)
            for key, value in fields.items():
                setattr(record, key, value)
        except (IndexError, ValueError, AttributeError) as e:
            print(e)
            pass  # Message is not formatted for json parsing
        return True


def get_workers_logger(host=GRAYLOG_HOST, port=GRAYLOG_PORT):
    logger = logging.getLogger('workers')
    logger.setLevel(logging.INFO)
    if GRAYLOG_HOST is not None:
        handler = graypy.GELFUDPHandler(host, int(port))
        handler.addFilter(GraylogLogFilter())
        logger.addHandler(handler)
    return logger


graylog_logger = get_workers_logger()


@app.route('/recommend_tags/', methods=['GET'])
def recommend_tags():
    input_tags_raw = request.args.get('input_tags', '')
    max_number_of_tags_raw = request.args.get('max_number_of_tags')

    input_tags = [tag.strip() for tag in input_tags_raw.split(',') if tag.strip()]

    max_number_of_tags = None
    if max_number_of_tags_raw is not None:
        try:
            max_number_of_tags = int(max_number_of_tags_raw)
        except ValueError:
            return jsonify({
                'error': True,
                'result': 'max_number_of_tags must be an integer',
            }), 400
        
    recommended_tags, community_name = tag_recommender.recommend_tags(input_tags, max_number_of_tags=max_number_of_tags)
    recommended_tags = recommended_tags[:max_number_of_tags] if max_number_of_tags is not None else recommended_tags

    if max_number_of_tags is not None:
        fake_recommendations = fake_recommendations[:max(0, max_number_of_tags)]

    if LOG_TO_GRAYLOG:
        response_for_logging = {
            'input_tags': input_tags,
            'max_number_of_tags': max_number_of_tags,
            'recommended_tags': recommended_tags,
            'community': community_name,
        }
        graylog_logger.info(f'Tag recommendation ({json.dumps(response_for_logging)})')

    return jsonify({
        'error': False,
        'result': {
            'tags': recommended_tags,
            'community': community_name,
        },
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)  # noqa: S104
