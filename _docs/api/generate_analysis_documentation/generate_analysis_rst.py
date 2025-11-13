import csv
import json
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

Most descriptors have ``fixed length`` and are divided into ``one-dimensional`` (descriptors that consist 
of a single value, e.g. pitch, note_name) and ``multi-dimensional`` (descriptors with several dimensions, e.g. tristimulus).
The remaining descriptors have ``variable length``, i.e. their length depends on the analyzed sound (denoted with `VL` in ``mode``).

All ``one-dimensional`` descriptors (regardless their ``type``) can be used in the ``filter`` parameter of the :ref:`sound-search` resource.
The ``multi-dimensional`` and ``variable-length`` descriptors can be accessed through the sound metadata 
(use ``fields`` parameter in any API resource that returns a sound list or the :ref:`sound-analysis`).
If ``mode`` ends with a number in parentheses (``n``), it indicates that this descriptor is ``multi-dimensional``, 
and this mode is calculated for a specific number of values.  
For example, if ``mode`` is ``mean (36)``, it represents the mean calculated across 36 values.

"""

curl_str = "    curl https://freesound.org/api/sounds/<sound_id>/analysis/"
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

    print("\n**Distribution in Freesound**\n")
    print(image_str + descriptor["name"] + ".png")
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
