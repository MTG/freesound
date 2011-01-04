#!/bin/sh

START=$(zcat $1 | grep -n "COPY auth_user (" | cut -f1 -d:)
echo "Starting substitutions on line: $START."
END=$(zcat $1 | sed -n "$START,$ p" | grep -m 1 -n "^\\\\\." | cut -f1 -d:)
END=$(($END + $START))
echo "Ending substitutions on line: $END."
echo "Starting substitutions... (be patient)"
zcat $1 | sed "$START,$END s/^\([0-9]\{1,\}[\t]\{1,\}[^\t]\{1,\}[\t]\{1,\}\)[A-Za-z0-9._%-]\{1,\}@[A-Za-z0-9.-]\{1,\}.[A-Za-z]\{2,4\}/\1anonymous@example.org/g" | gzip -c > $2
echo "Done"
