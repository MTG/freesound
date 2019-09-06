#!/bin/bash

echo "> Installing swig 3.0.12..."
# Install newer version of swig (gaia fails with swig 3.0.8)
sudo apt-get install libpcre3-dev autotools-dev automake
wget -O swig-3.0.12.tar.gz https://github.com/swig/swig/archive/rel-3.0.12.tar.gz
tar -xzf swig-3.0.12.tar.gz
cd swig-rel-3.0.12
./autogen.sh
./configure
make
sudo make install
cd ..

echo "> Cloning Gaia repo..."
git clone https://github.com/MTG/gaia.git

echo "> Installing Gaia..."
cd gaia
./waf configure --with-python-bindings
./waf
sudo ./waf install
# move gaia file to the virtual env
cp -r /usr/local/lib/python2.7/dist-packages/gaia2/ /home/travis/virtualenv/python2.7.15/lib/python2.7/site-packages/
