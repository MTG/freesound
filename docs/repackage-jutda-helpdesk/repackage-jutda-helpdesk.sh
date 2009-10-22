#!/bin/bash
# repackage-jutda-helpdesk.sh
#
# Adds a setup.py script to the jutda-helpdesk Django application and
# generates a tarball for installing with pip.

svn checkout -r140 http://jutda-helpdesk.googlecode.com/svn/trunk/ jutda-helpdesk
python setup.py sdist

    