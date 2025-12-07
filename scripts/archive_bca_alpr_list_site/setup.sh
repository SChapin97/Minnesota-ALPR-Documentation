#!/bin/sh

python3 -m virtualenv venv

. venv/bin/activate

which python

pip install playwright beautifulsoup4

playwright install chromium

echo "If all went well, run python bca_list_of_alprs_download.py"
