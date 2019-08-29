#!/bin/sh

SESSION_NAME="ds_corpus"
CARRAIGE_RETURN="C-m"
ABSOLUTE_PATHS_TO_OPEN=(
  "~/.captain/headproxy/ds-most-important-phrases-in-corpus-api"
  "~/.captain/headproxy/ds-most-important-phrases-in-corpus-drone"
)
tmux has-session -t ${SESSION_NAME}

if [ $? != 0 ];then
  # Create the new session
  tmux new-session -s ${SESSION_NAME} -d

  # Loop through all paths to open
  for path in "${ABSOLUTE_PATHS_TO_OPEN[@]}"; do
    tmux send-keys -t ${SESSION_NAME} "cd $path" ${CARRAIGE_RETURN}
    tmux new-window -n bash -t ${SESSION_NAME}
  done

  # kills the last window made, that was extra cause of our for loop
  tmux kill-window

  # First window (0) -- vim and console
  #tmux send-keys -t ${SESSION_NAME} 'vim' ${CARRAIGE_RETURN}

  # shell (1)
  #tmux new-window -n bash -t ${SESSION_NAME}
  #tmux send-keys -t ${SESSION_NAME}:1 'git status' ${CARRAIGE_RETURN}

  # Start out on the first window when we attach
  tmux select-window -t ${SESSION_NAME}:0
fi
# Attach to the newly created or previously existed session
tmux attach -t ${SESSION_NAME}