# Audio Descriptor Analysis Documentation

These scripts regenerate the audio-descriptor documentation and its plots.
Run them from inside this folder.

Everything starts from **`descriptors.csv`** — one row per descriptor. 
Edit it whenever the descriptors change. The distribution plots also read the per-descriptor value
dumps from `../audio_descriptors_values/`.

### The scripts

| Script | What it does |
|---|---|
| `generate_plots.py` | Builds a distribution plot per descriptor, saved directly into `../source/_static/descriptors/` (where the per-descriptor docs pick them up automatically) |
| `generate_resources_descriptor_table.py` | Prints the descriptor table for the Sound Instance resource (paste into `../source/resources.rst`) |
| `generate_analysis_rst.py` | Prints the full analysis docs page code (and handles the plot display) |

# Instructions for updating descriptors documentation

1) Update `descriptors.csv``
2) Run `python generate_resources_descriptor_table.py` and copy the printed table to the corresponding place in ` ../source/resources.rst`
3) Run `python generate_analysis_rst.py  > ../source/analysis_docs.rst` to update the analysis documentation page with new descriptors. This will add distribution images to the docs if these are present in the `../source/_static/descriptors/` folder. The first time a descriptor is deployed, it might need to be first added without a distribution image. When the descriptor is deployed in Freesound, then a command can be run to extract its values and generate the images. See next steps...
4) To create images for new descriptors (or update existing ones), the descriptor needs to be deployed in Freesound, and the its data exported to a JSON file with the command `export_audio_descriptor_stats --names xxx`. Then copy the resulting JSON file(s) here, and run the script `generate_plots.py` which will place new images in the correct location. Finally, re-run step 3) to update the docs. You can copy the descriptors with a command similar to `rsync -avz fs-cdn:/mnt/data/fsweb/audio_descriptors_values /home/ffont/Freesound/freesound/_docs/api/generate_analysis_documentation`

Note that to run `generate_plots.py` you'll need a python environment with 'seaborn', 'numpy' and 'matplotlib'
