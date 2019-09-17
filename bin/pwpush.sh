#!/bin/bash

# Usage:
#        pwpush.sh "contents of the secret" [flags]
#        cat secretFile | pwpush.sh [flags]
#
#   flags:
#       -v int                      views (default: 3)
#       -t int                      time (default: 5)
#       -u [days|hours|minutes]     unit (default: days)

URL="https://pwpush.madwire.net/index.php"

# check for tty
if [[ -t 0 ]] ; then
    UPSTR="$1"
    shift
else
    UPSTR=$(cat)
fi

# flags
while getopts "v:t:u:" OPT
do
    case $OPT in
    v)
        VIEWS="$OPTARG"
        ;;
    t)
        TIME="$OPTARG"
        ;;
    u)
        UNIT="$OPTARG"
        if [[ "$UNIT" != "days" && "$UNIT" != "minutes" && "$UNIT" != "hours" ]]; then
            echo "Invalid unit $UNIT; must be days,minutes,hours"
            exit 1
        fi
        ;;
    esac
done

RES=$(curl -s -X POST -H "application/x-www-form-urlencoded" --data-urlencode "cred=$UPSTR" --data-urlencode "views=$VIEWS" --data-urlencode "time=$TIME" --data-urlencode "unit=$UNIT" "$URL"  | perl -0777 -pe "s|\s+||g" | sed -e "s/.*<code>\(.*\)<\/code>.*/\1/")

echo $RES
