import csv
import json
import urllib.request

header = """
.. _analysis-docs:

Analysis Descriptor Documentation
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

.. contents::
    :depth: 3
    :backlinks: top


Analysis Settings
>>>>>>>>>>>>>>>>>

The analysis sample rate is 44100Hz and the audio file's channels are mixed down
to mono. For the lowlevel namespace the frame size is 2048 samples with a hop
size of 1024, while for the tonal namespace the frame size is 4096 and the hop size 2048.


Glossary 
>>>>>>>>>>>>>>>>

Basic terms used in the documentation of audio descriptors:

========= =====================================
numeric   The descriptor returns a numeric value; can be either an integer or a float.
integer   The descriptor returns an integer value only.
string    The descriptor returns a textual value.
boolean   The descriptor returns a binary value; 0 (no) or 1 (yes).
array[x]  The descriptor returns a list of elements of type X.
VL        Variable-length descriptor; the returned list may vary in length depending on the sound.
mean      The arithmetic mean of the descriptor values over the entire sound.
min       The lowest (minimum) descriptor value over the entire sound.
max       The highest (maximum) descriptor value over the entire sound.
var       The variance of the descriptor values over the entire sound.
========= =====================================

If ``Mode`` ends with a number in parentheses (``X``), it indicates that this mode is calculated for a specific number of values.  
For example, if ``Mode`` is ``mean (36)``, it represents the mean calculated across 36 values.

.. All single-value descriptors with type string or single numeric value can be used for filtering. 

"""

curl_str = "    curl https://freesound.org/api/sounds/<sound_id>/analysis/"
image_str = "    .. image:: _static/descriptors/"
height_str = "        :height: 300px"
desc_exceptions = []

example_url = "https://freesound.org/api/sounds/1234/analysis/?api_key=53b80e4d8a674ccaa80b780372103680&all=True"

# req = urllib.request.Request(example_url)
# resp = urllib.request.urlopen(req)
# top = json.loads(resp.read())

descriptors = []
with open("descriptors.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        descriptors.append({
            "name": row["Descriptor name"].strip(),
            "mode": row["Mode"].strip(),
            "type": row["Type"].strip(),
            "advanced": row["Complexity"].strip(),
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

    print("\n**Distribution in Freesound**\n")
    print(image_str + descriptor["name"] + ".png")
    print(height_str)
    print("\n")

# Split descriptors by complexity
main_descriptors = [d for d in descriptors if d.get("advanced").strip() != "advanced"]
advanced_descriptors = [d for d in descriptors if d.get("advanced").strip() == "advanced"]

print("Descriptors (main)")
print(">>>>>>>>>>>>>>>>\n")
for descriptor in main_descriptors:
    print_descriptor(descriptor)

print("Descriptors (advanced)")
print(">>>>>>>>>>>>>>>>\n")
for descriptor in advanced_descriptors:
    print_descriptor(descriptor)
