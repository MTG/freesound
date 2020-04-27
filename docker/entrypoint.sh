#!/bin/bash

set -e

if [[ $(id -u) != 0 ]]; then
    echo Must run entrypoint.sh as root
    exit 1
fi

if [[ -v FS_USER_ID && $FS_USER_ID != 0 && -n $FS_USER_ID ]]; then
    echo Set fsweb UID to: "$FS_USER_ID"
    usermod -u "$FS_USER_ID" fsweb

    exec gosu fsweb "$@"
else
    exec "$@"
fi