#!/bin/sh

SESSION_NAME="ds_cluster"
CARRAIGE_RETURN="C-m"
NAME_OR_COMMANDS_TO_RUN=(
  "winterfell"
  "ssh winterfell"
  "harrenhal"
  "ssh harrenhal"
)
DEFAULT_WINDOW_NAME=0

echo "checking if $SESSION_NAME already exists"
tmux has-session -t $SESSION_NAME

if [ $? != 0 ];then
  # Create the new session
  echo "creating session named $SESSION_NAME, as it doesn't exist"
  tmux new-session -s $SESSION_NAME

  # Loop through all paths to open
  for (( i=0; i<${#NAME_OR_COMMANDS_TO_RUN[@]} ; i+=2 )) ; do
    window_name=${NAME_OR_COMMANDS_TO_RUN[i]}
    command=${NAME_OR_COMMANDS_TO_RUN[i+1]}

    # create window
    echo "creating window named $window_name on session $SESSION_NAME"
    tmux new-window -n $window_name -t $SESSION_NAME

    # rename window
    echo "renaming window from $DEFAULT_WINDOW_NAME to $window_name"
    tmux rename-window -t $DEFAULT_WINDOW_NAME $window_name

    # run command
    echo "running command $command"
    tmux send-keys -t $SESSION_NAME "$command" $CARRAIGE_RETURN
  done

  # Start out on the first window when we attach
  # tmux select-window -t ${SESSION_NAME}:0
fi

# Attach to the newly created or previously existed session
echo "attaching to session named $SESSION_NAME"
tmux attach -t $SESSION_NAME