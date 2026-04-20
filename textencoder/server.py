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


import laion_clap
from flask import Flask, jsonify, request

app = Flask(__name__)

models = ["laion_clap"]

clap_model_path = "/630k-audioset-fusion-best.pt"
model = laion_clap.CLAP_Module(enable_fusion=True)
model.load_ckpt(clap_model_path)


def get_clap_embeddings_from_text(text):
    text_embed = model.get_text_embedding([text])
    text_embed = text_embed[0, :]
    return text_embed


@app.route("/encode_text/", methods=["GET"])
def encode_text():
    input = request.args.get("input", "")
    requested_model = request.args.get("model", None)

    embeddings = {}

    for model in [m for m in models if m == requested_model or requested_model is None]:
        if model == "laion_clap":
            embeddings[model] = get_clap_embeddings_from_text(input).tolist()

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
