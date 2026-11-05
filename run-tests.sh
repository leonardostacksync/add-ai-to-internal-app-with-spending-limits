#!/bin/sh
# Run every test in the repo. Needs Python 3.9+ and Node 18+.
set -e
cd "$(dirname "$0")/code"
(cd python-client && python3 -m unittest)
(cd budget && python3 -m unittest)
(cd key-policy && python3 -m unittest)
(cd node-client && node --test)
(cd server-proxy && node --test)
echo "all tests passed"
