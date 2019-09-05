#!/bin/bash

echo "> Installing swig 3.0.12..."
# Install newer version of swig (gaia fails with swig 3.0.8)
sudo apt-get install libpcre3-dev
wget -O swig-3.0.12.tar.gz https://downloads.sourceforge.net/project/swig/swig/swig-3.0.12/swig-3.0.12.tar.gz?r=https%3A%2F%2Fsourceforge.net%2Fprojects%2Fswig%2Ffiles%2Fswig%2Fswig-3.0.12%2Fswig-3.0.12.tar.gz%2Fdownload&ts=1486782132&use_mirror=superb-sea2
tar xf swig-3.0.12.tar.gz
cd swig-3.0.12
./configure --prefix=/usr
make -j 4
sudo make install
cd ..

echo "> Cloning Gaia repo..."
git clone https://github.com/MTG/gaia.git

echo "> Installing Gaia..."
cd gaia
./waf configure --with-python-bindings
./waf
sudo ./waf install
