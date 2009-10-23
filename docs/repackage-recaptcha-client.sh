#!/bin/bash
# repackage-recaptcha-client.sh
#
# recaptcha-client setup.py tries to 'import ez_setup'. This doesn't works 
# This script adds it to the root directory and generates a new package.

# download tarball
wget 'http://pypi.python.org/packages/source/r/recaptcha-client/recaptcha-client-1.0.4.tar.gz'
tar -xzf recaptcha-client-1.0.4.tar.gz
rm recaptcha-client-1.0.4.tar.gz

# download ez_setup.py
wget http://peak.telecommunity.com/dist/ez_setup.py -O recaptcha-client-1.0.4/ez_setup.py
# include on the dist
echo "include ez_setup.py" >> recaptcha-client-1.0.4/MANIFEST.in
# edit the version so we can know it's not the original package
sed -i 's/1.0.4/1.0.4-with.ez.setup/' recaptcha-client-1.0.4/setup.py
# repackage
cd recaptcha-client-1.0.4/
./setup.py sdist


