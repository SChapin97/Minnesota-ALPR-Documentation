#!/bin/sh

if [ -d "venv" ]; then
#    echo "venv exists"
    . venv/bin/activate
else
#    echo "venv does not exist"
    sh setup.sh
    . venv/bin/activate
fi

new_filename="$(date -I)_bca_alpr_list.json"

python bca_list_of_alprs_download.py

latest_alpr_file=$(ls alpr_list_changes/ | sort -n | tail -n 1)

new_lines=$(diff alpr_list_changes/"$latest_alpr_file" lpr_agencies.json)

if [ "$new_lines" ]; then
    echo "New lines in today's file:"
    echo "$new_lines"

    mv lpr_agencies.json alpr_list_changes/"$new_filename"
else
    echo "No new lines in today's file, deleting today's file"
    rm lpr_agencies.json
fi

rm -rf venv
