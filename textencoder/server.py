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


from flask import Flask, jsonify, request

app = Flask(__name__)


models = ["clap"]


@app.route("/encode_text/", methods=["GET"])
def encode_text():
    input = request.args.get("input", "")
    requested_model = request.args.get("model", None)

    embeddings = {}

    for model in [m for m in models if m == requested_model or requested_model is None]:
        # Compute embedding here
        fake_vector = [0.0] * 512
        embeddings[model] = fake_vector

    return jsonify(
        {
            "error": False,
            "result": {
                "embeddings": embeddings,
            },
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)  # noqa: S104
