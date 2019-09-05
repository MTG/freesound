#!/bin/bash

echo "> Cloning Gaia repo..."
git clone git@github.com:MTG/gaia.git

echo "> Installing Gaia..."
cd gaia
./waf configure --with-python-bindings
./waf
./waf install
