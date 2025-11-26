all: py2 py3

py2:
	docker build --platform linux/amd64 -t freesound:2023-07-py2 -f Dockerfile.py2.base .

py3:
	docker build --platform linux/amd64 -t freesound:2025-03 -f Dockerfile.base .

.PHONY: all py2 py3
