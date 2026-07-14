#!/bin/sh
set -e
if [ -d /app/wedding.db ]; then
    rm -rf /app/wedding.db
    touch /app/wedding.db
fi
exec "$@"
