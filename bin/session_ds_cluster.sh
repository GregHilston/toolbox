#!/bin/sh

session_name="ds_cluster"
carriage_return="C-m"
name_or_commands_to_run=(
  "winterfell"
  "ssh winterfell"
  "harrenhal"
  "ssh harrenhal"
  "reach"
  "ssh reach"
)
default_window_name=0

# check if session already exists
tmux has-session -t $session_name

if [ $? != 0 ];then
  # Create the new session if it does not exist
  tmux new-session -d -A -s $session_name
  # Loop through name and commands to run
  for (( i=0; i<${#name_or_commands_to_run[@]} ; i+=2 )) ; do
    window_name=${name_or_commands_to_run[i]}
    command=${name_or_commands_to_run[i+1]}

    if (($i == 0));then
      first_window_name=$window_name
    fi
    # create window
    echo "creating window named $window_name on session $session_name"
    tmux new-window -n $window_name -t $session_name

    # rename window
    echo "renaming window to $window_name"
    tmux rename-window $window_name

    # run command
    echo "running command $command"
    tmux send-keys -t $session_name "$command" $carriage_return
  done

  # kill default window
  echo "killing default window $default_window_name"
  tmux kill-window -t $default_window_name

  # Start out on the first window when we attach
  echo "selecting-window first window $session_name:$first_window_name"
  tmux select-window -t $session_name:$first_window_name
fi

# attach to built up session
echo "attaching to $session_name"
tmux attach-session -t $session_name