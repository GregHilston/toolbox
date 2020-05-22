#!/bin/bash
#Author: ZyX
#Link: https://stackoverflow.com/a/2916159

line="$(cat; echo -n a)"
end_offset=${#line}
while [[ "${line:0:$end_offset}" =~ (.*)(\$\{([a-zA-Z_][a-zA-Z_0-9]*)\})(.*) ]] ; do
    PRE="${BASH_REMATCH[1]}"
    POST="${BASH_REMATCH[4]}${line:$end_offset:${#line}}"
    VARNAME="${BASH_REMATCH[3]}"
    eval 'VARVAL="$'$VARNAME'"'
    line="$PRE$VARVAL$POST"
    end_offset=${#PRE}
done
echo -n "${line:0:-1}"
