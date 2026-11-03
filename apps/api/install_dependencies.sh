#!/bin/sh
set -eu
pip install --no-cache-dir uv==0.12.21
uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt
pip install --no-cache-dir --require-hashes -r /tmp/requirements.txt
pip uninstall -y uv
rm /tmp/requirements.txt
