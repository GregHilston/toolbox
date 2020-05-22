#!/bin/bash

mkdir -p "bin"

build_config()
{

    header="$(cat "header.conf" | ./replacer.sh)"
    execs="$(cat "exec.conf" | ./replacer.sh)"
    assignments="$(cat "assignments.conf" | ./replacer.sh)"
    keybinds="$(cat "keybinds.conf" | ./replacer.sh)"
    export MODEBINDS="$(cat "modebinds.conf" | ./replacer.sh)"
    export BANKBINDS="$(cat "template_bankbinds.conf" | ./replacer.sh)"
    MONITORS="$(cat "template_monitors.conf" | ./replacer.sh)"
    BANKTEXT=""
    bankfiles="$(find "./banks/" -type f)"
    sizebanks=1
    while [[ "$sizebanks" -gt "0" ]]; do
        bankfile="$(echo "$bankfiles" | sed -n "1p")"
	source "$bankfile"
	#echo "$bankfile"
	export BANK=$(echo $bankfile | rev | cut -d/ -f1 | rev | sed 's/\.conf//')
	BANKTEXT="$BANKTEXT\n$(cat "template_bank.conf" | ./replacer.sh)"
	bankfiles="$(echo "$bankfiles" | grep -v "^$bankfile\$")"
        sizebanks=${#bankfiles}
    done
    
    printf "${header}\n${execs}\n${keybinds}\n${MODEBINDS}\n${MONITORS}\n${assignments}\n${BANKTEXT}\n" > "$HOME/.config/i3/config"
    
    #printf "${MONITORS}\n"
}


get_monitors()
{
    monitors="$(xrandr | grep " connected " | cut -d' ' -f1)"
    count=$(echo "$monitors" | wc -l)
    MONITORNUM=${MONITORNUM:-1}
    realmax=$(( $MONITORNUM > $count ? $MONITORNUM : $count ))
    iteration=1
    strset=""

    while [[  "$iteration" -le "$realmax" ]]; do
	echo "Size: $size" > /dev/tty
        count=$(echo "$monitors" | wc -l)
        echo "Please enter a number for monitor $iteration:" > /dev/tty
    	echo "$(echo "$monitors" | nl -b a)" > /dev/tty
        read num
        selection="$(echo "$monitors" | sed -n "${num}p")" > /dev/tty
	echo "You chose: $selection" > /dev/tty
	varname="MONITOR$iteration"
        strset="$strset $varname=$selection;export $varname;"
	#export $(eval "echo ${varname}")
	#monitors="$(echo "$monitors" | grep -v "^$selection\$")"
	iteration=$((iteration+1))
    done
    echo "$strset"
}


# ---- START FLAGS ----
POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -m|--monitors)
    MONITORNUM="$2"
    shift # past argument
    shift # past value
    ;;
    -s|--searchpath)
    SEARCHPATH="$2"
    shift # past argument
    shift # past value
    ;;
    -l|--lib)
    LIBPATH="$2"
    shift # past argument
    shift # past value
    ;;
    --default)
    DEFAULT=YES
    shift # past argument
    ;;
    *)    # unknown option
    POSITIONAL+=("$1") # save it in an array for later
    shift # past argument
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters
# ---- END FLAGS ----



eval "$(get_monitors)"

build_config
i3 reload
i3 restart
