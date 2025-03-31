#!/bin/bash

uv pip compile requirements.in -o requirements.txt
uvx pip-licenses --python /usr/local/bin/python3 --output-file ACKNOWLEDGMENTS
