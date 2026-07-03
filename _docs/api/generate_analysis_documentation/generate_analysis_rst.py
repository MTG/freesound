import csv
import glob
import json
import os
import re
import urllib.request

header = """
.. _analysis-docs:

Audio Descriptors Documentation
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

.. contents::
    :depth: 3
    :backlinks: top


Analysis settings
>>>>>>>>>>>>>>>>>

Most of the available descriptors come from Essentia_, while some come from related initiatives such as the AudioCommons_ project.

.. _Essentia: https://essentia.upf.edu/
.. _AudioCommons: http://www.audiocommons.org/

During analysis, the sample rate is 44,100Hz and the audio file's channels are mixed down
to mono. For most descriptors, the frame size is 2,048 samples with a hop size of 1,024,
while for some tonal descriptors, the frame size is 4,096 samples with a hop size of 2,048.


"""

curl_str = "    curl https://freesound.org/api/sounds/<sound_id>/analysis/"
image_folder = '../source/_static/descriptors/'
image_str = "    .. image:: _static/descriptors/"
height_str = "        :height: 300px"

descriptors = []
with open("descriptors.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        descriptors.append({
            "name": row["Descriptor name"].strip(),
            "mode": row["Mode"].strip(),
            "type": row["Type"].strip(),
            "complexity": row["Complexity"].strip(),
            "description": row["Description"].strip(),
            "values": row.get("Range", "").strip(),
            "links": row.get("Links", "").strip()
        })

print(header)

def print_descriptor(descriptor):
    """Print a single descriptor in formatted documentation style."""
    print(descriptor["name"])
    print("-------------------------")
    print("\n::\n")
    print(curl_str + descriptor["name"])

    print("\n**Description:** " + descriptor["description"])

    mode = descriptor.get("mode")
    if mode and mode != "-":
        print("\n**Mode:** " + mode)

    if descriptor.get("type"):
        print("\n**Type:** " + descriptor["type"])

    if descriptor.get("values"):
        print("\n**Values:** " + descriptor["values"])

    if descriptor.get("links"):
        print("\n**More information:** " + descriptor["links"])

    image_paths = (
        glob.glob(os.path.join(image_folder, f"{descriptor['name']}.png"))
        or glob.glob(os.path.join(image_folder, f"{descriptor['name']}-*.png"))  #descriptor_[number]
    )
            
    if image_paths:
        image_paths.sort(key=lambda p: int(re.findall(r'\d+', os.path.basename(p))[-1]) if re.findall(r'\d+', os.path.basename(p)) else -1)
        print("\n**Distribution in Freesound**\n")
        for image_path in image_paths:
            print(f"{image_str}{os.path.basename(image_path)}")
            print(height_str)

    print("\n")

# Split descriptors by complexity
main_descriptors = [d for d in descriptors if d.get("complexity").strip() != "advanced"]
advanced_descriptors = [d for d in descriptors if d.get("complexity").strip() == "advanced"]

print("Main set of descriptors")
print(">>>>>>>>>>>>>>>>\n")
for descriptor in main_descriptors:
    print_descriptor(descriptor)

print("Advanced set of descriptors")
print(">>>>>>>>>>>>>>>>\n")
for descriptor in advanced_descriptors:
    print_descriptor(descriptor)
