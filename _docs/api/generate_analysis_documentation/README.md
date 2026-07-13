# Audio Descriptor Analysis Documentation

These scripts regenerate the audio-descriptor documentation and its plots.
Run them from inside this folder.

Everything starts from **`descriptors.csv`** — one row per descriptor. 
Edit it whenever the descriptors change. The distribution plots also read the per-descriptor value
dumps in `../descriptors/`.

### The scripts

| Script | What it does |
|---|---|
| `generate_plots.py` | Builds a distribution plot per descriptor, saved directly into `../source/_static/descriptors/` (where the per-descriptor docs pick them up automatically) |
| `generate_resources_descriptor_table.py` | Prints the descriptor table for the Sound Instance resource (paste into `../source/resources.rst`) |
| `generate_analysis_rst.py` | Prints the full analysis docs page code (and handles the plot display) |

`generate_plots.py` writes its files directly, nothing to move. 
The other two just print RST to the terminal, so you copy-paste (or pipe) their output into the docs.
`generate_analysis_rst.py` prints the whole page, so you can redirect it straight to its source file:

```bash
python generate_plots.py

python generate_resources_descriptor_table.py   # copy output into ../source/resources.rst

python generate_analysis_rst.py > ../source/analysis_docs.rst
```
