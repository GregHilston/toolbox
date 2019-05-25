#!/bin/bash

# echo $HOME
# echo $SUDO_USER

# echo getent passwd $HOME | cut -d: -f6
# echo getent passwd $SUDO_USER | cut -d: -f6

# reference https://stackoverflow.com/a/39296583/1983957
if [[ -z "${SUDO_USER}" ]]; then
		echo "${HOME}" # default value, as $SUDO_USER is not set
	else
		USER_NAME_WHO_RAN="${SUDO_USER}"	
		echo $(getent passwd ${USER_NAME_WHO_RAN} | cut -d: -f6)
fi
