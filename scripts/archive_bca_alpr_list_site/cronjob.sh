#!/bin/sh

#0 9 * * * sh <location>/cronjob.sh
sh archive_alpr_list_changes.sh  | grep -A 100 "Successfully installed" | grep -v "Successfully installed"
