# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# -- Project information -----------------------------------------------------

project = "Freesound API"
copyright = "Universitat Pompeu Fabra"
author = "Frederic Font"
version = "2.0"
release = "2.0"

# -- General configuration ---------------------------------------------------

extensions = ["add_examples_to_api_docs_source_files"]
templates_path = ["_templates"]
# Included by resources_apiv2.rst to preserve the published page URL.
exclude_patterns = ["resources.rst"]

# -- Options for HTML output -------------------------------------------------

html_theme = "freesound"
html_theme_path = ["_themes"]
html_title = "Freesound API documentation"
html_static_path = ["_static"]
html_use_index = False
pygments_style = "sphinx"
htmlhelp_basename = "FreesoundAPIdoc"

# -- Options for LaTeX output ------------------------------------------------

latex_documents = [
    ("index", "FreesoundAPI.tex", "Freesound API Documentation", author, "manual"),
]
