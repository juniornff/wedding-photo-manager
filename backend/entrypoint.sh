#!/bin/sh
set -e
for dir in /app/data /app/Fotos /app/Miniaturas; do
    [ -d "$dir" ] || mkdir -p "$dir"
    owner="$(stat -c '%u:%g' "$dir")"
    [ "$owner" = "1000:1000" ] || chown -R app:app "$dir"
done
exec python3 -c "
import os, sys
os.setgid(1000)
os.setuid(1000)
os.execvp(sys.argv[1], sys.argv[1:])
" "$@"
