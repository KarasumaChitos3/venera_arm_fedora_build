#!/bin/sh

# Attempt to run from lib64 first, fallback to lib.
if [ -x "/usr/lib64/venera/venera" ]; then
  exec "/usr/lib64/venera/venera" "$@"
elif [ -x "/usr/lib/venera/venera" ]; then
  exec "/usr/lib/venera/venera" "$@"
else
  echo "venera binary not found in /usr/lib64/venera or /usr/lib/venera" >&2
  exit 1
fi