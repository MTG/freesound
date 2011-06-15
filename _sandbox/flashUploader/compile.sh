#!/bin/sh

mxmlc -target-player=10.0 src/Upload.as -output ./upload.swf

mv upload.swf ../../media/swf/upload.swf
