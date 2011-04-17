#!/bin/sh

mxmlc -target-player=10.0 LargePlayer.as
mxmlc -target-player=10.0 MediumPlayer.as

mv LargePlayer.swf ../../../media/swf/LargePlayer.swf
mv MediumPlayer.swf ../../../media/swf/MediumPlayer.swf