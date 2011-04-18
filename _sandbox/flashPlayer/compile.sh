#!/bin/sh

mxmlc -target-player=10.0 src/LargePlayer.as -output ./LargePlayer.swf
mxmlc -target-player=10.0 src/MediumPlayer.as -output ./MediumPlayer.swf

mv LargePlayer.swf ../../media/swf/LargePlayer.swf
mv MediumPlayer.swf ../../media/swf/MediumPlayer.swf
