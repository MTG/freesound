"""Expand API examples when Sphinx reads the resource documentation."""

import runpy
from pathlib import Path
from urllib.parse import quote

BASE_URL = "https://freesound.org/"
EXAMPLES_PATH = Path(__file__).resolve().parents[2] / "apiv2" / "examples.py"


def get_formatted_examples_for_view(view_name, examples):
    output = ""
    for description, elements in examples[view_name]:
        output += f"\n\n{description}:\n\n"
        output += "::\n\n"
        for element in elements:
            if element.startswith("apiv2"):
                output += "  {}{}\n".format(BASE_URL, quote(element, safe='?/=&",:()'))
            else:
                output += f"  {element % BASE_URL.rstrip('/')}\n"
    return output


def expand_examples(app, relative_path, parent_docname, content):
    if relative_path != Path("resources.rst"):
        return

    app.env.note_dependency(str(EXAMPLES_PATH))
    examples = runpy.run_path(str(EXAMPLES_PATH))["examples"]
    lines = []
    for line in content[0].splitlines(keepends=True):
        if "{{examples_" in line:
            name = line.split("{{examples_", 1)[1].split("}}", 1)[0]
            lines.append(get_formatted_examples_for_view(name, examples) + "\n")
        else:
            lines.append(line)
    content[0] = "".join(lines)


def setup(app):
    app.connect("include-read", expand_examples)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
